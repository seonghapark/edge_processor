#!/bin/bash

if [[ ! -e /home/waggle/finish_test ]]; then
  echo "Creating /home/waggle/start_test file..."
  touch /home/waggle/start_test

  echo "Mounting alternate boot medium..."
  . /usr/lib/waggle/core/scripts/detect_disk_devices.sh
  mount | grep '/media/test' && true
  if [ $? -eq 1 ]; then
    umount /media/test
  fi
  mount "${OTHER_DISK_DEVICE}p2" /media/test

  echo "Creating /home/waggle/start_test file on alternate boot medium..."
  touch /media/test/home/waggle/start_test

  echo "Unmounting alternate boot medium..."
  umount /media/test
fi

echo "Starting test service..."
sudo /bin/systemctl start waggle-test.service
