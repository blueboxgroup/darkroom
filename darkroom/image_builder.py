# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2014, Craig Tracey
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations

import logging
import os
import socket
import shutil
import sys
import tempfile
import time

from fabric.api import cd, env, execute, get, put, run, sudo
from novaclient import client as nova

from darkroom.build_instance_settings import BuildInstanceSettings

LOG = logging.getLogger(__name__)


class ImageBuilder(object):

    def __init__(self, settings):
        self._settings = settings
        self._build_instance_settings = BuildInstanceSettings(settings)
        self._nova_client = None
        self._build_instance = None
        self._build_instance_fip = None
        self._build_tempdir = None

    @staticmethod
    def supported_distros():
        raise NotImplementedError()

    def _get_openstack_credentials(self):
        creds = {}
        creds['username'] = os.environ['OS_USERNAME']
        creds['api_key'] = os.environ['OS_PASSWORD']
        creds['auth_url'] = os.environ['OS_AUTH_URL']
        creds['project_id'] = os.environ['OS_TENANT_NAME']
        return creds

    def _get_nova_client(self):
        creds = self._get_openstack_credentials()
        self._nova_client = nova.Client('1.1', **creds)

    def _create_builder_instance(self):
        params = self._build_instance_settings
        nics = [{"net-id": params.net_id}]
        LOG.info("Launched build instance: %s", params.name)
        instance = self._nova_client.servers.create(name=params.name,
                                                    image=params.image,
                                                    nics=nics,
                                                    flavor=params.flavor,
                                                    key_name=params.key_name)

        status = instance.status
        while status == 'BUILD':
            LOG.info("Waiting for build instance to be ready (status: %s)",
                     status)
            time.sleep(5)
            instance = self._nova_client.servers.get(instance.id)
            status = instance.status
        self._build_instance = instance

    def _attach_floating_ip(self):
        floating_ips = self._nova_client.floating_ips.list()
        fip = None
        for floating_ip in floating_ips:
            if floating_ip.instance_id is None:
                fip = floating_ip.ip
                break
        if not fip:
            raise Exception("No free floating IP's found")
        self._nova_client.servers.add_floating_ip(self._build_instance, fip)
        self._build_instance_ip = fip

    def _install_builder_requirements(self):
        packer_url = self._build_instance_settings.packer_url
        output = execute(ImageBuilder.install_builder_requirements,
                         packer_url, hosts=[self._build_instance_ip])
        self._build_tempdir = output[self._build_instance_ip]

    @staticmethod
    def install_builder_requirements(packer_url):
        tempdir = run('mktemp -d')
        sudo('apt-get update')
        sudo('apt-get install -y unzip qemu')
        with cd(tempdir):
            run('wget %s -O packer.zip && unzip packer.zip' % packer_url)
        return tempdir

    def _copy_files_to_builder(self):
        kickstart_path = self.kickstart_path
        packer_config = self.get_packer_config()
        output = execute(ImageBuilder.copy_files_to_builder,
                         self._build_tempdir, packer_config, kickstart_path,
                         hosts=[self._build_instance_ip])

    @staticmethod
    def copy_files_to_builder(tempdir, packer_config, kickstart_path):
        local_tempdir = tempfile.mkdtemp()
        local_packer_path = os.path.join(local_tempdir, 'packer_config.json')
        with open(local_packer_path, 'w') as f:
            f.write(packer_config)

        with cd(tempdir):
            run('mkdir httpdir')
            put(kickstart_path, 'httpdir/kickstart.cfg')
            put(local_packer_path, 'packer_config.json')
        shutil.rmtree(local_tempdir)

    def _run_packer(self):
        execute(ImageBuilder.run_packer, self._build_tempdir,
                hosts=[self._build_instance_ip])

    @staticmethod
    def run_packer(tempdir):
        with cd(tempdir):
            sudo('PACKER_LOG=1 && ./packer build packer_config.json')

    def _get_image_from_remote(self):
        output = execute(ImageBuilder.get_image_from_remote,
                         self._build_tempdir,
                         self._build_instance_settings.name,
                         hosts=[self._build_instance_ip])

    @staticmethod
    def get_image_from_remote(tempdir, build_dir_name):
        local_path = os.path.join(os.getcwd(), build_dir_name)
        os.makedirs(build_dir_name)
        with cd(tempdir):
            get('packer_output', local_path)

    def _wait_for_ssh(self):
        interval = 5
        retries = 60
        count = 0

        for x in range(retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect((self._build_instance_ip, 22))
                time.sleep(interval)  # give an extra 5 secs to get going
                return True
            except socket.error as e:
                LOG.info("SSH not available yet...")
                time.sleep(interval)
        return False

    def build(self):
        # build an instance to work with
        self._get_nova_client()
        LOG.info("Building builder instance")
        self._create_builder_instance()
        LOG.info("Attaching a floating IP")
        self._attach_floating_ip()

        if not self._wait_for_ssh():
            raise Exception("SSH never became available")

        # now start provisioning on that instance
        env.user = self._build_instance_settings.user
        env.forward_agent = True
        env.disable_known_hosts = True

        self._install_builder_requirements()
        self._copy_files_to_builder()
        self._run_packer()
        self._get_image_from_remote()

    def cleanup(self):
        LOG.info("Cleanup not implemented yet.")
        sys.exit(-1)


from darkroom.builders.rhel import RhelImageBuilder


def get_image_builder(settings):
    distro = settings.get('distro', None)
    version = settings.get('version', None)
    if distro in RhelImageBuilder.supported_distros():
        return RhelImageBuilder(settings)
    raise Exception("Unknown distro %s and/or version %s" % (distro, version))
