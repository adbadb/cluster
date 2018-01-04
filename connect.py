#!/usr/bin/env python
"""

Script to connect to most recent instance whose id or name has substring

Usage:
To connect to most recently launched instance:
  connect

To connect to most recently launched instance containing 5i3 either in instance id or in instance name:
  connect 5i3

To connect to most recent instance with name simple
  connect simple


"""

# todo: allow to do ls, show tags
# todo: handle KeyError: 'PublicIpAddress'

import boto3
import time
import sys
import os
from datetime import datetime
from operator import itemgetter

import util as u

import argparse
parser = argparse.ArgumentParser(description='Launch CIFAR training')
parser.add_argument('--skip-tmux', type=int, default=0,
                    help='whether to skip TMUX launch')
parser.add_argument('--fragment', type=str, default='',
                    help='fragment to filter by')
args = parser.parse_args()


def toseconds(dt):
  # to invert:
  # import pytz
  # utc = pytz.UTC
  # utc.localize(datetime.fromtimestamp(seconds))
  return time.mktime(dt.utctimetuple())

def main():
  fragment = args.fragment

  region = os.environ['AWS_DEFAULT_REGION']
  client = boto3.client('ec2', region_name=region)
  ec2 = boto3.resource('ec2', region_name=region)
  response = client.describe_instances()

  username = os.environ.get("USERNAME", "ubuntu")
  print("Using username '%s'"%(username,))
    
  instance_list = []
  for instance in ec2.instances.all():
    if instance.state['Name'] != 'running':
      continue
    
    name = u.get_name(instance.tags)
    if (fragment in name or fragment in instance.public_ip_address or
        fragment in instance.id or fragment in instance.private_ip_address):
      instance_list.append((toseconds(instance.launch_time), instance))
      
  import pytz
  from tzlocal import get_localzone # $ pip install tzlocal

  sorted_instance_list = sorted(instance_list, key=itemgetter(0))
  cmd = ''
  print("Using region ", region)
  for (ts, instance) in reversed(sorted_instance_list):
    localtime = instance.launch_time.astimezone(get_localzone())
    assert instance.key_name == u.RESOURCE_NAME, "Got key %s, expected %s"%(instance.key_name, u.RESOURCE_NAME)
    keypair_fn = u.get_keypair_fn(instance.key_name)

  print("Connecting to %s in %s launched at %s with key %s" % (u.get_name(instance.tags), region, localtime, instance.key_name))

  if args.skip_tmux:
    cmd = "ssh -i %s -o StrictHostKeyChecking=no %s@%s" % (keypair_fn, username, instance.public_ip_address)
  else:
    cmd = 'connect_helper.sh %s %s %s'%(keypair_fn, username,
                                        instance.public_ip_address)
  
  if not cmd:
    print("no instance id contains fragment '%s'"%(fragment,))
  else:
    print(cmd)
    os.system(cmd)



if __name__=='__main__':
  main()
