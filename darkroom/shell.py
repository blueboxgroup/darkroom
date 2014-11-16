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

import argparse
import logging
import signal
import sys
import yaml

import darkroom.image_builder

def _setup_logger():
    logger = logging.getLogger()
    log_handler = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(fmt='%(asctime)s %(name)s %(levelname)s: '
                            '%(message)s', datefmt='%F %H:%M:%S')
    log_handler.setFormatter(fmt)
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)


def main():
    parser = argparse.ArgumentParser(description='Build some openstack images')
    parser.add_argument('config_file')

    _setup_logger()
    LOG = logging.getLogger(__name__)

    args = parser.parse_args()

    settings = None
    with open(args.config_file, 'r') as fh:
        settings = yaml.load(fh)
    builder = darkroom.image_builder.get_image_builder(settings)

    def signal_handler(*args):
        LOG.info("Interrupted. Cleaning up...")
        builder.cleanup()

    signal.signal(signal.SIGINT, signal_handler)
    builder.build()


if __name__ == '__main__':
    main()
