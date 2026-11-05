import os,time,subprocess,signal,json,math
os.environ['ROS_LOG_DIR']='/tmp/roslogs'
import rclpy
from sensor_msgs.msg import LaserScan
rclpy.init(); n=rclpy.create_node('audit_scan_reader'); samples=[]; first=None

def callback(m):
 global first
 now=time.monotonic(); samples.append((now,m.header.stamp.sec+m.header.stamp.nanosec/1e9))
 if first is None:
  finite=[x for x in m.ranges if math.isfinite(x) and m.range_min<=x<=m.range_max]
  first={'frame':m.header.frame_id,'stamp':[m.header.stamp.sec,m.header.stamp.nanosec],'points':len(m.ranges),'intensities':len(m.intensities),'angle_min':m.angle_min,'angle_max':m.angle_max,'angle_increment':m.angle_increment,'scan_time':m.scan_time,'time_increment':m.time_increment,'range_min':m.range_min,'range_max':m.range_max,'valid':len(finite),'zero':sum(x==0 for x in m.ranges),'nan':sum(math.isnan(x) for x in m.ranges),'nearest_m':min(finite) if finite else None,'furthest_m':max(finite) if finite else None}
sub=n.create_subscription(LaserScan,'/scan',callback,10)
cmd=['/root/yahboomcar_ws/install/oradar_lidar/lib/oradar_lidar/oradar_scan','--ros-args']
params={'port_name':'/dev/ttyAMA1','baudrate':230400,'device_model':'MS200','frame_id':'laser_frame','scan_topic':'/scan','angle_min':0.0,'angle_max':360.0,'range_min':0.05,'range_max':20.0,'clockwise':'false','motor_speed':10}
for k,v in params.items(): cmd+=['-p',f'{k}:={v}']
p=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
try:
 deadline=time.monotonic()+12
 while time.monotonic()<deadline and p.poll() is None: rclpy.spin_once(n,timeout_sec=.2)
 endpoints=[{'node':x.node_name,'type':x.topic_type,'qos':str(x.qos_profile)} for x in n.get_publishers_info_by_topic('/scan')]
 print(json.dumps({'samples':len(samples),'elapsed_samples_s':samples[-1][0]-samples[0][0] if len(samples)>1 else None,'hz':(len(samples)-1)/(samples[-1][0]-samples[0][0]) if len(samples)>1 else None,'first':first,'publishers':endpoints}),flush=True)
finally:
 p.send_signal(signal.SIGINT)
 try: log=p.communicate(timeout=3)[0]
 except subprocess.TimeoutExpired: p.kill();log=p.communicate()[0]
 print('DRIVER_EXIT',p.returncode,'\n'+log); n.destroy_node(); rclpy.shutdown()
