import pathlib,json,subprocess,zipfile
out={}
for base in ['/home/pi/DOGZILLA','/home/pi/.config/autostart']:
 for p in pathlib.Path(base).rglob('*'):
  if p.is_file() and p.suffix in ['.py','.sh','.desktop'] and p.stat().st_size<300000:
   out[str(p)]=p.read_text(errors='replace')
for f in ['/etc/systemd/system/yahboom_oled.service','/boot/firmware/config.txt','/home/pi/run_humble.sh']:
 out[f]=pathlib.Path(f).read_text()
for p in pathlib.Path('/usr/local/lib/python3.11/dist-packages').glob('DOGZILLA*.egg'):
 with zipfile.ZipFile(p) as z: out[str(p)+'!DOGZILLALib.py']=z.read('DOGZILLALib/DOGZILLALib.py').decode()
for cmd in ['timedatectl','sudo -n fuser -v /dev/ttyAMA0 /dev/ttyAMA1 /dev/video0','docker ps -a','ip -br addr','df -h','ss -lntup']:
 out[cmd]=subprocess.getoutput(cmd)
print(json.dumps(out))
