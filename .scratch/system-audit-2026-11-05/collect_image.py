import pathlib,json,zipfile,hashlib
out={}
for base in ['/root/yahboomcar_ws/src','/root/yahboomcar_ws/install','/root/DOGZILLALib']:
 for p in pathlib.Path(base).rglob('*'):
  if not p.is_file() or any(x in p.parts for x in ['.git','build','log','__pycache__']): continue
  if p.stat().st_size>300000: continue
  if p.suffix not in ['.py','.cpp','.h','.yaml','.xml','.xacro','.urdf','.lua','.msg','.srv','.action','.txt','.sh','.cfg'] and p.name!='CMakeLists.txt': continue
  try: out[str(p)]=p.read_text()
  except Exception: pass
for p in pathlib.Path('/usr/local/lib/python3.10/dist-packages').glob('DOGZILLA*.egg'):
 with zipfile.ZipFile(p) as z: out[str(p)+'!DOGZILLALib.py']=z.read('DOGZILLALib/DOGZILLALib.py').decode()
out['/root/.bashrc']=pathlib.Path('/root/.bashrc').read_text()
out['AMENT_INDEX']='\n'.join(str(p) for p in pathlib.Path('/opt/ros/humble/share/ament_index/resource_index/packages').glob('*'))
print(json.dumps(out))
