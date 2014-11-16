darkroom - a tool to build openstack images via packer
======================================================
darkroom is a tool that aids the process of creating images for an openstack cloud.  This tool wraps [Packer](http://packer.io), and performs all the image creation steps within one's own cloud.

Install
=======
```
user@somehost:~/src/darkroom$ mkvirtualenv darkroom
New python executable in darkroom/bin/python
Installing setuptools, pip...done.
(darkroom)user@somehost:~/src/darkroom$ pip install pbr
(darkroom)user@somehost:~/src/darkroom$ python setup.py install
```

Configuration
=============
```yaml
---
name: centos5.11
distro: centos
version: '5.11'
kickstart_path: kickstarts/kickstart.centos5.cfg

build_instance:
  key_name: openstack
  flavor: 3
  image: ce268db5-ceda-4a90-93c8-3b987ac3705f
  user: ubuntu
  net_id: ba0fdd03-72b5-41eb-bb67-fef437fd6cb4
```

Usage
=====
```
user@somehost:~/src/darkroom$ source stackrc
user@somehost:~/src/darkroom$ darkroom config.yml
```

License
=======
|                      |                                                    |
|:---------------------|:---------------------------------------------------|
| **Authors**          |  Craig Tracey (<craigtracey@gmail.com>)            |
|                      |                                                    |
| **Copyright**        |  Copyright (c) 2014, Craig Tracey                  |

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
