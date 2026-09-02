# Vector Reclassify QGIS Plugin

ปลั๊กอินนี้เพิ่มหน้าต่างใน QGIS สำหรับ reclassify ค่า attribute ของชั้นข้อมูล Vector แบบ exact match แล้วบันทึกผลเป็น layer ใหม่

ผู้สร้างปลั๊กอิน: Passakorn Poonkerd

Repository: https://github.com/rmutsv007/vector-reclassify

## ความสามารถหลัก

- เลือกได้หลาย vector layer พร้อมกัน (checkbox list) แล้วรัน rule ชุดเดียวกับทุก layer ทีเดียว
- แต่ละ layer ประมวลผลแยกกัน ถ้า layer ใด error จะไม่หยุดการทำงานของ layer อื่น และมีสรุปผลสำเร็จ/ล้มเหลวหลังรันเสร็จ
- กำหนดชื่อ field ใหม่สำหรับเก็บค่าหลัง reclassify
- สร้างกฎ map ค่าแบบ `from -> to` หลายรายการ
- สลับระหว่างโหมดตารางกับโหมดลากวางได้ โดยยังเก็บ rule ที่ทำไว้
- เลือกหลายแถว/หลายค่าพร้อมกันแล้ว bulk assign target value หรือ assign เข้า class เดียวกันได้ทีเดียว
- มีช่องค้นหา/กรอง rule และไฮไลต์แถวที่ยังไม่ได้กรอก target value ก่อนกด OK
- บันทึก/โหลดชุด rule เป็นไฟล์ preset (`.json`) และมีเมนู recent presets ให้เลือกใช้ซ้ำ
- ปุ่ม "Preview coverage" แสดงจำนวน record ที่ match/ไม่ match rule ก่อนรันจริง แยกตาม layer
- จำค่า output type/format และ checkbox ที่เคยตั้งไว้ล่าสุด เปิดครั้งถัดไปไม่ต้องตั้งใหม่
- โหลดค่า unique จาก field ที่เลือกมาเติมในตาราง rule อัตโนมัติ
- เลือกเก็บค่าเดิมเมื่อไม่พบ rule หรือปล่อยเป็นค่าว่างได้
- ส่งออกเป็น temporary Shapefile ได้ และตั้งเป็นค่าเริ่มต้นของ dialog
- ส่งออกเป็น `.gpkg`, `.shp`, หรือ `.geojson` โดยเลือกชนิดไฟล์ตรงๆ ผ่าน dropdown (เมื่อเลือกหลาย layer จะส่งออกลง folder เดียวกัน ไฟล์ละ layer)
- จำกัดการประมวลผลเฉพาะ selected features ได้

## โครงสร้างไฟล์

- `__init__.py` จุดเริ่มต้นของ QGIS plugin
- `metadata.txt` metadata สำหรับ Plugin Manager
- `icon.svg` ไอคอนของปลั๊กอินสำหรับ toolbar และ Plugin Manager
- `vector_reclassify_plugin.py` ผูกเมนูและ toolbar เข้ากับ QGIS
- `vector_reclassify_dialog.py` สร้าง dialog สำหรับรับค่าจากผู้ใช้
- `reclassifier.py` logic สำหรับเขียน output layer ใหม่
- `package_plugin.ps1` สคริปต์สำหรับสร้าง zip พร้อมแจกจ่าย

## วิธีติดตั้งแบบ local plugin

1. zip โฟลเดอร์นี้ทั้งโฟลเดอร์ โดยให้ `metadata.txt` อยู่ที่ root ของ zip
2. ใน QGIS ไปที่ `Plugins > Manage and Install Plugins... > Install from ZIP`
3. เลือก zip ที่สร้างไว้ แล้วติดตั้ง

อีกวิธีคือคัดลอกโฟลเดอร์นี้ไปไว้ใน plugin directory ของ QGIS เช่น

- Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\VectorReclassify`

จากนั้น restart QGIS หรือ reload plugin

## การแพ็กปลั๊กอินสำหรับแจกจ่าย

รันคำสั่งนี้จากโฟลเดอร์โปรเจ็กต์:

```powershell
.\package_plugin.ps1
```

สคริปต์จะสร้างไฟล์ zip ในโฟลเดอร์ `dist` โดยมีโครงสร้างภายในเป็นโฟลเดอร์ `VectorReclassify` ซึ่งพร้อมใช้กับ `Install from ZIP` และเหมาะสำหรับใช้เป็น release artifact

## วิธีใช้งาน

1. เปิดเมนู `Vector > Vector Reclassify`
2. เลือก layer หนึ่งหรือหลาย layer ในลิสต์ (ใช้ปุ่ม Select all / Clear selection ช่วยได้) และเลือก source field
3. ระบุ `New field name` เช่น `landuse_class`
4. เลือกโหมดแก้ไข rule แบบตารางหรือแบบลากวาง แล้วกำหนด mapping เช่น `101 -> Urban`, `102 -> Agriculture`
   - เลือกหลายแถว/หลายค่าพร้อมกันแล้วกด "Bulk assign target..." หรือ "Assign selected to class..." เพื่อกำหนดค่าให้ทีเดียว
   - ใช้ช่อง Filter ค้นหา rule เมื่อ unique values เยอะ แถวที่ยังไม่กรอก target value จะถูกไฮไลต์สีแดงอ่อน
   - บันทึก mapping ที่ทำไว้เป็น preset (`Save preset...`) เพื่อนำไปใช้ซ้ำกับ layer อื่น หรือโหลดจาก `Load preset...` / เมนู Recent presets
5. กด `Preview coverage...` เพื่อดูจำนวน record ที่ match/ไม่ match ก่อนรันจริง
6. เลือก output format ที่ต้องการ ถ้าใช้ temporary file ระบบจะสร้างไฟล์ให้อัตโนมัติ (ไฟล์เดียวหรือหลายไฟล์ตามจำนวน layer) แต่ถ้าระบุ output path เอง: เลือก layer เดียวให้ระบุไฟล์ปลายทาง, เลือกหลาย layer ให้ระบุ folder ปลายทาง (ระบบตั้งชื่อไฟล์ตาม layer ให้อัตโนมัติ)
7. กด `OK` เพื่อสร้าง layer ใหม่ ถ้ามี layer ใด error ระบบจะแจ้งสรุปแยกเป็นรายตัว โดยไม่กระทบ layer ที่สำเร็จ

## ข้อจำกัดของเวอร์ชันนี้

- reclassify แบบ exact match เท่านั้น
- target field ต้องเป็น field ใหม่ ยังไม่รองรับ overwrite field เดิม
- ถ้าเลือก output type เป็น `Integer` หรือ `Double` ค่าที่ map ต้องแปลงเป็นตัวเลขได้
- เมื่อเลือกหลาย layer พร้อมกัน ทุก layer ต้องมี source field ชื่อเดียวกันตามที่เลือกไว้ (layer ที่ไม่มี field นี้จะรายงาน error แยกแต่ไม่กระทบ layer อื่น)