#!/usr/bin/env python
# Tools for EFS related tasks
# By default, lists all volumes, along with their availability zones and attacment points

# TODO: clone tool to create clones of an EBS disk

import boto3
import sys
import os
import time

from operator import itemgetter

import util as u

def list_ebss_by_instance():
  """Print list of instances with their attached volume id/size to console, ie
master-us-east-1a.masters.df86c4e8-pachydermcluster.kubernetes.com: vol-0f0e841d0cc657002 (20),vol-06fb03280cf2598fb (20),vol-0e7ef0896b234db53 (64)
nodes.df86c4e8-pachydermcluster.kubernetes.com: vol-012367900cd8dae8c (128)
nodes.df86c4e8-pachydermcluster.kubernetes.com: vol-0a98ee5f7f155b2b7 (128),vol-048e29f604d2900a7 (100)
imagenet: vol-024347797a6ab11e8 (1500)
api_service_prod: vol-0c36c9f21bb6be8a6 (8)
box00.gpubox.0: vol-0c69c68295a89cde5 (50)
  """

  ec2 = u.create_ec2_resource()
  instances = [(u.seconds_from_datetime(i.launch_time), i) for i in ec2.instances.all()]
  sorted_instances = sorted(instances, key=itemgetter(0))

  for (seconds, instance) in sorted_instances:

    volumes = instance.volumes.all()
    volume_strs = []
    for v in volumes:
      volume_strs.append("%s (%s)"%(v.id, v.size))
    print("%s: %s" % (u.get_name(instance.tags), ','.join(volume_strs)))

def list_ebss():
  """."""

  ec2 = u.create_ec2_resource()

  volumes = list(ec2.volumes.all())
  for vol in volumes:
    vol_name = u.get_name(vol)
    if not vol_name:
      vol_name = vol.id
    attached_to = []
    if vol.attachments:
      for attachment in vol.attachments:
        instance_id = attachment["InstanceId"]
        instance=ec2.Instance(instance_id)
        attached_to.append(u.get_name(instance))
    else:
      attached_to.append('<unattached>')

    print("%25s %s %s"%(vol_name, vol.availability_zone, attached_to))
    
def grow_ebs_for_task(task_fragment, target_size_gb):
  """Grows EBS volume for given task."""

  ec2 = u.create_ec2_resource()
  client = u.create_ec2_client()

  # todo: don't crash on missing/duplicate names
  instances = {u.get_name(i.tags): i for i in ec2.instances.all()}

  ec2 = u.create_ec2_resource()
  instances = [(u.seconds_from_datetime(i.launch_time), i) for i in ec2.instances.all()]
  sorted_instances = reversed(sorted(instances, key=itemgetter(0)))

  for (seconds, instance) in sorted_instances:
    task_name = u.get_name(instance.tags)
    hours_ago = (time.time()-seconds)/3600
    hours_ago+=8 # adjust for time being in UTC

    if task_fragment in task_name:
      print("Found instance %s launched %.1f hours ago" %( task_name, hours_ago))
      break
  print(instance.id)

  volumes = list(instance.volumes.all())
  assert len(volumes)==1, "Must have 1 volume"

  print("Growing %s to %s"%(volumes[0].id, target_size_gb))
  response = client.modify_volume(
      VolumeId=volumes[0].id,
      Size=target_size_gb,
  )
  assert u.is_good_response(response)

def main():
  if len(sys.argv) < 2:
    mode = 'list'
  else:
    mode = sys.argv[1]

  if mode == 'list':
    list_ebss()
  elif mode == 'grow':
    task_fragment = sys.argv[2]
    grow_ebs_for_task(task_fragment, 500)
  else:
    assert False, "Unknown mode "+mode
      
if __name__=='__main__':
  main()
