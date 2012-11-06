#!/usr/bin/env python

import roslib; roslib.load_manifest("falkor_drivers")
import rospy
from serial import *
from sensor_msgs.msg import *
from geometry_msgs.msg import *
from std_msgs.msg import *
import numpy as np

class RazorDriver:
    def __init__(self):
        self.timeout = rospy.get_param( "~timeout", 5.0 )
        self.port = rospy.get_param( "~port", "/dev/ttyUSB0" )
        self.baud = rospy.get_param( "~baud", 57600 )

        self.port = Serial(self.port, self.baud, timeout=self.timeout * 0.5)
    
        self.mag_topic = rospy.get_param( "~mag_topic", "imu/mag" )
        self.imu_topic = rospy.get_param( "~imu_topic", "imu/data_raw" )

        self.tf_prefix = rospy.get_param( "~tf_prefix", "" )
        self.mag_frame = self.tf_prefix + "/" + rospy.get_param( "~mag_frame", "magnetometer" )
        self.imu_frame = self.tf_prefix + "/" + rospy.get_param( "~imu_frame", "imu" )

        self.mag_pub = rospy.Publisher( self.mag_topic, Vector3Stamped )
        self.imu_pub = rospy.Publisher( self.imu_topic, Imu )
        self.mag_seq = 0
        self.imu_seq = 0

    def run(self):
        while not rospy.is_shutdown():
            line = self.port.readline()
            now = rospy.Time.now()

            if line[1] != '$' or line[-3] != '#':
                raise Exception( "invalid IMU data line: %s" % line )

            split_line = line[2:-3].split(',')
            split_line_ints = [int(a) for a in split_line]
            accel = split_line_ints[0:3]
            gyro = split_line_ints[3:6]

            self.imu_seq += 1
            imu_msg = Imu()
            imu_msg.header = Header( self.imu_seq,
                                     now, self.imu_frame )
            imu_msg.orientation = Quaternion( 0, 0, 0, 1.0 )
            imu_msg.orientation_covariance = [0] * 9

            gyro = np.array( gyro ) / 14.375 / 180.0 * np.pi
            imu_msg.angular_velocity = Vector3( *gyro )
            imu_msg.angular_velocity_covariance = [0] * 9

            accel = np.array( accel ) / 256.0 * 9.82
            imu_msg.linear_acceleration = Vector3( *accel )
            imu_msg.linear_acceleration_covariance = [0] * 9
            self.imu_pub.publish( imu_msg )

            if len( split_line_ints ) > 6:
                self.mag_seq += 1

                header = Header( self.mag_seq, now, self.mag_frame )
                mag = split_line_ints[6:9]
                mag = np.array( mag ) / np.linalg.norm( mag )
                mag_msg = Vector3Stamped( header, Vector3( *mag ) )
                self.mag_pub.publish( mag_msg )

def main():
    rospy.init_node('razor_driver')
    driver = RazorDriver()
    try:
        driver.run()
    except KeyboardInterrupt:
        print "Shutting down"

if __name__  == '__main__':
    main()

