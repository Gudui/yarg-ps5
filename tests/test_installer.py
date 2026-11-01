import ftplib,hashlib,io,json,struct,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import yarg_ps5 as m

class FTP:
    def __init__(self,existing=(),fail_title=False,corrupt=False):
        self.dirs=set(existing)|{'/data','/data/homebrew','/data/prospero-win'};self.files={};self.renames=[];self.fail_title=fail_title;self.corrupt=corrupt
    def cwd(self,path):
        if path not in self.dirs:raise ftplib.error_perm('550 absent')
    def size(self,path):
        if path not in self.files:raise ftplib.error_perm('550 absent')
        return len(self.files[path])
    def mkd(self,path):
        if path in self.dirs:raise ftplib.error_perm('550 exists')
        self.dirs.add(path)
    def storbinary(self,command,stream,**kwargs):self.files[command[5:]]=b'corrupt' if self.corrupt else stream.read()
    def retrbinary(self,command,callback):
        if command[5:] not in self.files:raise ftplib.error_perm('550 absent')
        callback(self.files[command[5:]])
    def sendcmd(self,cmd):pass
    def rename(self,source,target):
        if self.fail_title and target=='/data/homebrew/PPSA99400':raise OSError('title rename refused')
        require=source in self.files or source in self.dirs
        assert require,(source,target)
        if source in self.files:self.files[target]=self.files.pop(source)
        else:
            self.dirs={target+p[len(source):] if p==source or p.startswith(source+'/') else p for p in self.dirs}
            self.files={target+p[len(source):] if p.startswith(source+'/') else p:b for p,b in self.files.items()}
        self.renames.append((source,target))

class Tests(unittest.TestCase):
    def stage(self,root):
        for name,b in [('homebrew/PPSA99400/eboot.bin',b'eboot'),('library/prefixes/yarg/system.reg',b'registry'),('library/profiles/yarg.profile',b'profile')]:
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        manifest=m.make_manifest(root,{})
        (root/'manifest.json').write_text(json.dumps(manifest));return manifest
    def test_archive_traversal_and_symlink_rejected(self):
        for name,mode in [('../escape',0),('/absolute',0),('C:/drive',0),('link',0o120777)]:
            with tempfile.TemporaryDirectory() as tmp:
                z=Path(tmp)/'a.zip';info=zipfile.ZipInfo(name);info.external_attr=mode<<16
                with zipfile.ZipFile(z,'w') as out:out.writestr(info,b'x')
                with self.assertRaises(ValueError):m.extract(z,Path(tmp)/'out')
    def test_hash_mismatch_never_enters_cache(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(m.urllib.request,'urlopen',return_value=io.BytesIO(b'wrong')):
            with self.assertRaises(ValueError):m.fetch({'url':'https://example.invalid/file','sha256':'0'*64},Path(tmp))
            self.assertFalse((Path(tmp)/('0'*64)).exists())
    def test_existing_title_or_prefix_preserved(self):
        for remote in ['/data/homebrew/PPSA99400','/data/prospero-win/prefixes/yarg']:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);manifest=self.stage(root);ftp=FTP([remote]);before=set(ftp.dirs)
                with self.assertRaises(ValueError):m.install(ftp,root,manifest,'test')
                self.assertEqual(ftp.dirs,before);self.assertFalse(ftp.files)
    def test_title_is_published_last_with_eboot_inside(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=self.stage(root);ftp=FTP();m.install(ftp,root,manifest,'test')
            self.assertEqual(ftp.renames[-1][1],'/data/homebrew/PPSA99400')
            self.assertEqual(ftp.files['/data/homebrew/PPSA99400/eboot.bin'],b'eboot')
    def test_title_failure_restores_unpublished_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=self.stage(root);ftp=FTP(fail_title=True)
            with self.assertRaises(OSError):m.install(ftp,root,manifest,'test')
            self.assertNotIn('/data/prospero-win/prefixes/yarg',ftp.dirs)
            self.assertNotIn('/data/prospero-win/profiles/yarg.profile',ftp.files)
    def test_bad_transfer_keeps_title_unpublished(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=self.stage(root);ftp=FTP(corrupt=True)
            with self.assertRaises(ValueError):m.install(ftp,root,manifest,'test')
            self.assertFalse(ftp.renames)
    def test_manifest_mutation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.stage(root);(root/'homebrew/PPSA99400/eboot.bin').write_bytes(b'changed')
            with self.assertRaises(ValueError):m.verify(root)
    def test_complete_local_package_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.stage(root)
            self.assertEqual(len(m.verify(root)['files']),3)
    def test_elf_normalization_never_omits_code(self):
        elf=bytearray(232);elf[:6]=b'\x7fELF\x02\x01';struct.pack_into('<Q',elf,32,64);struct.pack_into('<HH',elf,54,56,2)
        struct.pack_into('<IIQQQQQQ',elf,64,1,5,176,4096,4096,32,32,16)
        struct.pack_into('<IIQQQQQQ',elf,120,0x6fffff01,0,208,0,0,24,0,1)
        elf[176:208]=bytes(range(32));elf[208:]=b'v'*24
        row={'sha256':'not-signed','elf_sha256':m.canonical_elf(bytes(elf))}
        elf[208:]=bytes(24);m.remote_matches(bytes(elf),row)
        elf[180]^=1
        with self.assertRaises(ValueError):m.remote_matches(bytes(elf),row)

if __name__=='__main__':unittest.main()
