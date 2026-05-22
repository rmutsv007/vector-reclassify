# Vector Reclassify QGIS Plugin

ปลั๊กอินนี้เพิ่มหน้าต่างใน QGIS สำหรับ reclassify ค่า attribute ของชั้นข้อมูล Vector แบบ exact match แล้วบันทึกผลเป็น layer ใหม่

ผู้สร้างปลั๊กอิน: Passakorn Poonkerd

Repository: https://github.com/rmutsv007/vector-reclassify

## ความสามารถหลัก

- เลือก vector layer และ source field จากโปรเจ็กต์ปัจจุบัน
- กำหนดชื่อ field ใหม่สำหรับเก็บค่าหลัง reclassify
- สร้างกฎ map ค่าแบบ `from -> to` หลายรายการ
- สลับระหว่างโหมดตารางกับโหมดลากวางได้ โดยยังเก็บ rule ที่ทำไว้
- โหลดค่า unique จาก field ที่เลือกมาเติมในตาราง rule อัตโนมัติ
- เลือกเก็บค่าเดิมเมื่อไม่พบ rule หรือปล่อยเป็นค่าว่างได้
- ส่งออกเป็น temporary Shapefile ได้ และตั้งเป็นค่าเริ่มต้นของ dialog
- ส่งออกเป็น `.gpkg`, `.shp`, หรือ `.geojson`
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
2. เลือก layer และ field ต้นทาง
3. ระบุ `New field name` เช่น `landuse_class`
4. เลือกโหมดแก้ไข rule แบบตารางหรือแบบลากวาง แล้วกำหนด mapping เช่น `101 -> Urban`, `102 -> Agriculture`
5. ถ้าใช้ temporary file ระบบจะสร้างเป็น `.shp` เสมอ แต่ถ้าระบุ output path เอง ระบบจะดูชนิดไฟล์จากนามสกุลที่เลือก
6. กด `OK` เพื่อสร้าง layer ใหม่

## ข้อจำกัดของเวอร์ชันนี้

- reclassify แบบ exact match เท่านั้น
- target field ต้องเป็น field ใหม่ ยังไม่รองรับ overwrite field เดิม
- ถ้าเลือก output type เป็น `Integer` หรือ `Double` ค่าที่ map ต้องแปลงเป็นตัวเลขได้