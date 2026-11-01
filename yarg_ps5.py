#!/usr/bin/env python3
"""Prepare and install an unmodified Windows YARG Home-screen tile for prospero-win."""
from __future__ import annotations
import argparse,ftplib,hashlib,importlib.util,io,json,os,shutil,struct,subprocess,sys,tempfile,urllib.request,uuid,zipfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parent
TITLE='PPSA99400'

def require(ok,message):
    if not ok:raise ValueError(message)

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda:stream.read(1024*1024),b''):h.update(part)
    return h.hexdigest()

def relative(name):
    p=PurePosixPath(name)
    require(name and '\\' not in name and not p.is_absolute() and '..' not in p.parts and ':' not in name,'unsafe path: '+name)
    return p

def fetch(component,cache):
    cache.mkdir(parents=True,exist_ok=True)
    target=cache/component['sha256']
    if target.exists():
        require(digest(target)==component['sha256'],'cached download is corrupt: '+str(target))
        return target
    temporary=target.with_suffix('.incoming')
    print('Downloading '+component['url'],flush=True)
    with urllib.request.urlopen(component['url'],timeout=60) as response,temporary.open('wb') as stream:
        shutil.copyfileobj(response,stream)
    require(digest(temporary)==component['sha256'],'download hash mismatch: '+component['url'])
    temporary.replace(target)
    return target

def extract(archive,directory):
    seen=set()
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            name=relative(item.filename)
            require(str(name).casefold() not in seen,'duplicate archive path: '+str(name))
            seen.add(str(name).casefold())
            require((item.external_attr>>16)&0o170000 != 0o120000,'archive symlink rejected')
            dest=directory.joinpath(*name.parts)
            if item.is_dir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(item) as source,dest.open('wb') as stream:shutil.copyfileobj(source,stream)

def canonical_elf(data):
    require(data[:6]==b'\x7fELF\x02\x01','expected ELF64')
    require(len(data)>=64,'truncated ELF')
    off=struct.unpack_from('<Q',data,32)[0];size,count=struct.unpack_from('<HH',data,54)
    require(size>=56 and off+count*size<=len(data),'invalid ELF program headers')
    normalized=bytearray(data);omitted=[];loads=[]
    for i in range(count):
        kind,flags,start,va,pa,length,mem,align=struct.unpack_from('<IIQQQQQQ',data,off+i*size)
        require(start+length<=len(data),'ELF segment exceeds file')
        if kind==1:loads.append((start,start+length))
        if kind==0x6fffff01 or (kind==4 and length==24 and data[start+12:start+16]==b'SIE\0'):
            omitted.append((start,start+length))
    require(all(b<=c or a>=d for a,b in omitted for c,d in loads),'ELF metadata overlaps runtime')
    require(all(a>=off+count*size for a,b in omitted),'ELF metadata overlaps headers')
    for a,b in omitted:normalized[a:b]=bytes(b-a)
    return hashlib.sha256(normalized).hexdigest()

def portable_prefix(source,destination,module):
    files,dirs,links=module.local_tree(source)
    for name in dirs:destination.joinpath(*PurePosixPath(name).parts).mkdir(parents=True,exist_ok=True)
    for name,path in files.items():
        target=destination.joinpath(*relative(name).parts)
        if name in module.REGISTRY:target.write_bytes(module.to_console(name,path.read_bytes()))
        else:shutil.copyfile(path,target)
    for directory,table in links.items():
        text=''.join(f'{name}\t{value}\n' for name,value in sorted(table.items()))
        (destination/directory/module.LINK_TABLE).write_text(text,encoding='utf-8',newline='\n')

def load_module(path):
    spec=importlib.util.spec_from_file_location('pw_prefix',path);module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module;spec.loader.exec_module(module);return module

def make_manifest(directory,integrity):
    files={}
    for tree in ['homebrew','library']:
        for path in sorted((directory/tree).rglob('*')):
            require(not path.is_symlink(),'staged symlink: '+str(path))
            if path.is_file():
                name=path.relative_to(directory).as_posix();entry={'sha256':digest(path),'bytes':path.stat().st_size}
                if name in integrity:
                    require(entry['sha256']==integrity[name]['sha256'],'artifact differs from integrity provenance: '+name)
                    entry['elf_sha256']=integrity[name]['elf_sha256']
                files[name]=entry
    directories=[p.relative_to(directory).as_posix() for t in ['homebrew','library'] for p in (directory/t).rglob('*') if p.is_dir()]
    require(f'homebrew/{TITLE}/eboot.bin' in files,'title eboot missing')
    require('library/profiles/yarg.profile' in files,'YARG profile missing')
    return {'schema':1,'title_id':TITLE,'files':files,'directories':sorted(directories)}

def verify(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    require(manifest['schema']==1 and manifest['title_id']==TITLE,'wrong manifest')
    roots=[f'homebrew/{TITLE}/','library/prefixes/yarg/','library/profiles/yarg.profile']
    for name,row in manifest['files'].items():
        relative(name);require(any(name.startswith(r) for r in roots),'file outside install scope')
        p=directory.joinpath(*PurePosixPath(name).parts)
        require(not p.is_symlink() and p.is_file() and digest(p)==row['sha256'],'local mismatch: '+name)
    for name in manifest['directories']:
        relative(name);require(name in ['library/prefixes','library/profiles'] or any((name+'/').startswith(r) for r in roots),'directory outside install scope')
    actual={p.relative_to(directory).as_posix() for t in ['homebrew','library'] for p in (directory/t).rglob('*') if p.is_file()}
    require(actual==set(manifest['files']),'manifest does not exactly cover installation')
    return manifest

def prepare(args):
    require(os.name!='nt','Prefix preparation uses Linux/WSL. See README Windows instructions.')
    require(not args.output.exists(),'output exists; choose a new output directory')
    lock=json.loads((ROOT/'components.json').read_text());downloads={k:fetch(v,args.cache) for k,v in lock['downloads'].items()}
    with tempfile.TemporaryDirectory(prefix='yarg-ps5-') as temporary:
        work=Path(temporary);extract(downloads['runtime'],work/'runtime');extract(downloads['overlay'],work/'overlay');extract(downloads['source'],work/'source')
        candidates=list((work/'runtime').rglob('PPSA99995/eboot.bin'));require(len(candidates)==1,'unexpected prospero-win archive layout')
        tools=list((work/'source').rglob('tools/pw_install.py'));require(len(tools)==1,'unexpected source layout');upstream=tools[0].parent
        args.output.parent.mkdir(parents=True,exist_ok=True)
        stage=args.output.with_name(args.output.name+'.incoming-'+uuid.uuid4().hex[:8]);stage.mkdir()
        title=stage/'homebrew'/TITLE;shutil.copytree(candidates[0].parent,title)
        shutil.copytree(work/'overlay'/'title',title,dirs_exist_ok=True)
        metadata=json.loads((title/'sce_sys/param.json').read_text());require(metadata['titleId']==TITLE,'wrong title identity')
        environment=os.environ.copy();environment['WINEDEBUG']='-all'
        subprocess.run([sys.executable,str(upstream/'pw_install.py'),str(ROOT/'recipes/yarg.yml'),'--library',str(work/'library'),'--wine',str(args.wine),'--file','yarg='+str(downloads['yarg'])],check=True,env=environment)
        portable_prefix(work/'library/prefixes/yarg',stage/'library/prefixes/yarg',load_module(upstream/'pw_prefix.py'))
        for name,expected in lock['application_files'].items():
            require(digest(stage/'library/prefixes/yarg'/name)==expected,'official YARG identity mismatch: '+name)
        (stage/'library/profiles').mkdir(parents=True);shutil.copyfile(work/'library/profiles/yarg.profile',stage/'library/profiles/yarg.profile')
        integrity=json.loads((work/'overlay/integrity.json').read_text())
        manifest=make_manifest(stage,integrity);manifest['components']=lock
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        verify(stage);stage.rename(args.output)
    print('Prepared '+str(args.output)+'; YARG program files are unmodified.')

def exists(ftp,path):
    try:ftp.cwd(path);return True
    except ftplib.error_perm as error:
        if str(error).startswith('550'):return False
        raise

def mkdir(ftp,path):
    current=''
    for part in PurePosixPath(path).parts[1:]:
        current+='/'+part
        if not exists(ftp,current):ftp.mkd(current)

def read(ftp,path):
    data=[];ftp.retrbinary('RETR '+path,data.append);return b''.join(data)

def remote_matches(data,row):
    if hashlib.sha256(data).hexdigest()==row['sha256']:return
    require('elf_sha256' in row and canonical_elf(data)==row['elf_sha256'],'FTP read-back differs from package')

def install(ftp,directory,manifest,stamp):
    destinations=[('/data/prospero-win/prefixes/yarg','library/prefixes/yarg'),('/data/prospero-win/profiles/yarg.profile','library/profiles/yarg.profile'),('/data/homebrew/'+TITLE,'homebrew/'+TITLE)]
    require(not exists(ftp,'/mnt/sandbox/'+TITLE+'_000'),'YARG is running/suspended')
    for remote,local in destinations:
        require(not exists(ftp,remote),'existing installation preserved: '+remote)
        if local.endswith('.profile'):
            try:ftp.size(remote)
            except ftplib.error_perm as error:
                if not str(error).startswith('550'):raise
            else:raise ValueError('existing profile preserved: '+remote)
    work='/data/yarg-ps5-install-'+stamp
    ftp.mkd(work)
    for name in manifest['directories']:mkdir(ftp,work+'/'+name)
    for index,(name,row) in enumerate(manifest['files'].items(),1):
        remote=work+'/'+name;mkdir(ftp,str(PurePosixPath(remote).parent))
        with (directory/name).open('rb') as stream:ftp.storbinary('STOR '+remote,stream,blocksize=1024*1024)
        if name.endswith(('.bin','.prx','.elf')):ftp.sendcmd('SITE CHMOD 755 '+remote)
        remote_matches(read(ftp,remote),row)
        if index%100==0:print(f'Uploaded and verified {index}/{len(manifest["files"])}',flush=True)
    committed=[]
    try:
        require(not exists(ftp,'/mnt/sandbox/'+TITLE+'_000'),'YARG started during staging')
        for remote,local in destinations:
            require(not exists(ftp,remote),'destination appeared during staging')
            if local.endswith('.profile'):
                try:ftp.size(remote)
                except ftplib.error_perm as error:
                    if not str(error).startswith('550'):raise
                else:raise ValueError('profile appeared during staging')
            mkdir(ftp,str(PurePosixPath(remote).parent));ftp.rename(work+'/'+local,remote);committed.append((remote,local))
    except Exception:
        for remote,local in reversed(committed):ftp.rename(remote,work+'/'+local)
        raise
    return {'files':len(manifest['files']),'installed':[x[0] for x in destinations],'staging':work}

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('prepare');p.add_argument('--wine',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'dist');p.add_argument('--cache',type=Path,default=ROOT/'cache')
    p=commands.add_parser('verify');p.add_argument('directory',type=Path)
    p=commands.add_parser('deploy');p.add_argument('directory',type=Path);p.add_argument('--host',required=True);p.add_argument('--port',type=int,default=2121)
    args=parser.parse_args()
    try:
        if args.command=='prepare':prepare(args)
        elif args.command=='verify':print('Verified',len(verify(args.directory)['files']),'files')
        else:
            manifest=verify(args.directory)
            with ftplib.FTP() as ftp:
                ftp.connect(args.host,args.port,timeout=30);ftp.login()
                report=install(ftp,args.directory,manifest,uuid.uuid4().hex)
            (args.directory/'deploy-report.json').write_text(json.dumps(report,indent=2)+'\n');print('Installed. Refresh/register the YARG tile in ShadowMountPlus, then launch it from Home.')
    except (ValueError,OSError,subprocess.CalledProcessError,*ftplib.all_errors) as error:
        print('yarg-ps5: '+str(error),file=sys.stderr);return 1
    return 0

if __name__=='__main__':sys.exit(main())
