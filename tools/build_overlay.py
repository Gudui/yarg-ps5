#!/usr/bin/env python3
"""Package existing qualified artifacts; this does not build or contact a console."""
import argparse,hashlib,json,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from yarg_ps5 import canonical_elf,digest,require

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','native','stagec','fix','self-tool','output']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    c=json.loads((a.stagec/'manifest.json').read_text());fix=json.loads((a.fix/'manifest.json').read_text())
    require(digest(a.stagec/'manifest.json')=='fc07b738e61d8d578bd908ed18463db257522f82c88dbb7e38ca15ab4a443db1','wrong Stage C manifest')
    require(digest(a.fix/'manifest.json')=='1f221ebc86729aa0440ce9fa05d99e417aadce794210e9f906c19a5e180fef64','wrong startup-fix manifest')
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp);overlay=tmp/'overlay';title=overlay/'title';title.mkdir(parents=True)
        for path in a.native.rglob('*'):
            if path.is_file():
                dest=title/path.relative_to(a.native);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
        for package,rows in [(a.stagec,c['files']),(a.fix,fix['files'])]:
            for row in rows:
                prefix='/data/homebrew/PPSA99400/'
                if not row['remote'].startswith(prefix):continue
                src=package/row['local'];require(digest(src)==row['sha256'],'artifact hash mismatch')
                dest=title/row['remote'][len(prefix):];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
        require(digest(title/'eboot.bin')=='cbbc9f30c3c0ef8398bdd442bb360e73ef838a33188c9743a3333c0476dcb3c5','wrong YARG host')
        require(digest(title/'lapy.elf')=='5525c1deb7ffe70a3462a1aba3cf586c6ac0828d04af869b80466e22a69dc0e3','wrong title helper')
        source='''QUALIFIED YARG TILE OVERLAY
prospero-win source https://github.com/Gudui/prospero-win/tree/b76fe98a0635cea79064c7a2942f14452bcbb1c3
Native host and ntdll: b76fe98a0635cea79064c7a2942f14452bcbb1c3
Paired XInput PRX/PE: 9a67d5e60dbbd43c269cfb14031c0234b5bcb8b4 (sink unchanged in b76fe98)
Wine: 490f6d5dcbb2a5047345b8af88d114bbcaad69a8 plus that fork's patches, including upstream0986.
Native title foundation: 9c0b994a048521af6fb84c73ded364504fe250e9
Module foundation: 30597512539e7edfde079cbcaf4a626bc0a948c5
Title helper: retained PPSA99400 MIT Lapy helper; see LICENSES/Lapy-MIT.txt.
Title build: PW_TITLE_ID=PPSA99400 PW_TITLE_NAME=YARG PW_FIXED_PROFILE=yarg PW_HOME_EXIT_LOADEXEC=1 PW_USB360_CAPTURE=0.
Reproduction instructions: https://github.com/Gudui/yarg-ps5/blob/main/docs/BUILDING.md

ORIGINAL BASE RUNTIME PROVENANCE AND LICENSES FOLLOW
'''
        (title/'SOURCES.txt').write_text(source+(a.baseline/'SOURCES.txt').read_text(),encoding='utf-8')
        assembled=tmp/'assembled';shutil.copytree(a.baseline,assembled);shutil.copytree(title,assembled,dirs_exist_ok=True)
        integrity={}
        for path in assembled.rglob('*'):
            if not path.is_file():continue
            with path.open('rb') as stream:magic=stream.read(4)
            if magic!=bytes.fromhex('4f153d1d'):continue
            elf=tmp/'extract.elf'
            subprocess.run([str(a.self_tool),'self','--extract','--file',str(path),'--out',str(elf)],check=True,stdout=subprocess.DEVNULL)
            integrity['homebrew/PPSA99400/'+path.relative_to(assembled).as_posix()]={'sha256':digest(path),'elf_sha256':canonical_elf(elf.read_bytes())}
        (overlay/'integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for path in sorted(overlay.rglob('*')):
                if path.is_file():
                    info=zipfile.ZipInfo(path.relative_to(overlay).as_posix(),date_time=(2026,11,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                    z.writestr(info,path.read_bytes())
        print('OVERLAY_READY',digest(a.output),'integrity_files',len(integrity))

if __name__=='__main__':main()
