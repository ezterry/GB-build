#!/usr/bin/python
#pack apk files

import os
import os.path
import sys
import shutil
import re
import tempfile

ANDROID_BUILD_TOP=os.getenv("ANDROID_BUILD_TOP")
ANDROID_PRODUCT_OUT=os.getenv("ANDROID_PRODUCT_OUT")
TARGET_PRODUCT=os.getenv("TARGET_PRODUCT")
APKCERTS_INT=os.path.join(str(ANDROID_PRODUCT_OUT),"obj/PACKAGING/apkcerts_intermediates")
#PACKAGING/apkcerts_intermediates/full_sapphire-apkcerts-eng.ezterry.txt


def _getKey(apkname):
    keyfiles=filter(lambda fn:fn.startswith(TARGET_PRODUCT),
                    os.listdir(APKCERTS_INT))
    for fn in keyfiles:
        fp=open(os.path.join(APKCERTS_INT,fn),'r')
        for line in fp:
            m= re.match(r'name=\"([^\"]*)\" certificate=\"([^\"]*)\" private_key=\"([^\"]*)\"',line)
            if(m is not None and m.group(1)==apkname):
               fp.close()
               return ((os.path.join(ANDROID_BUILD_TOP,m.group(2)),
                        os.path.join(ANDROID_BUILD_TOP,m.group(3))))
        fp.close()
    return ((None,None))
    
def packAPK(data,name):
    """Pack an apk file as possible"""
    (cert, key) = _getKey(name)
    size=len(data)
    if(cert is None or key is None):
        print("ERROR: Could not find key for %s, Leaving unpacked" % (name,))
        return data
    
    print("%s:\n  cert=%s\n  key=%s\n" %(name,cert,key))
    
    #create a temporary directory
    tmproot = tempfile.mkdtemp(suffix="-apkpack")
    #put the current apk into said directory
    fp=open(os.path.join(tmproot,'work.apk'),'wb')
    fp.write(data)
    fp.close()
    
    #write compression script
    fp=open(os.path.join(tmproot,'compress.sh'),'w')
    fp.write("""#!/bin/sh
#change to work directory
cd '%s' 
#cert of the package
cert='%s'
#key of the package
key='%s'

unzip work.apk resources.arsc
zip -9 -r work.apk resources.arsc
rm resources.arsc
unzip work.apk *.png

for png in `find ./ | grep png$`
do
    echo crushing: $png
    pngcrush $png crush.png >> /dev/null
    rm $png
    mv crush.png $png
    zip -0 -r work.apk $png
    rm $png
done

#delete old key
zip -d work.apk META-INF/MANIFEST.MF
zip -d work.apk META-INF/CERT.SF
zip -d work.apk META-INF/CERT.RSA

#resign
java -jar $ANDROID_BUILD_TOP/out/host/*/framework/signapk.jar \
          $cert $key work.apk work_s.apk
#realign
$ANDROID_BUILD_TOP/out/host/*/bin/zipalign 4 work_s.apk work_a.apk
ls -l work_a.apk
""" % (tmproot,cert,key))
    fp.close()
    #run the above shell script
    os.system("sh " + os.path.join(tmproot,'compress.sh'))
    
    #now pick up the result
    try:
        fp=open(os.path.join(tmproot,'work_a.apk'),'rb')
        data = fp.read()
    except:
        print("Error: reading compressed apk")
        return data
    fp.close()
    shutil.rmtree(tmproot)
    print("Done: %d -> %d (%f%%)" % 
         (size,len(data),100.0*(len(data)/(size*1.0))))
    return data


if __name__ == "__main__":
    fn=None
    try:
        fn=sys.argv[1]
    except:
        pass
    if(fn is None or fn == "" or fn == "--help"):
        print("APK Packer usage:")
        print("%s <apk file>" % (sys.argv[0]))
        print("")
        print("APK must have a known apkcerts key in the build system")
        print("Also enviroment variables ANDROID_BUILD_TOP,")
        print("ANDROID_PRODUCT_OUT, and TARGET_PRODUCT must be set")
    else:
        fp=open(fn,'rb')
        data = fp.read()
        fp.close()
        fp=open(fn,'wb')
        fp.write(packAPK(data,os.path.basename(fn)))
        fp.close()
