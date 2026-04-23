# 📄 SPEC: แบบ 20 - คำร้องขอลงทะเบียนเรียนเพิ่ม
**Add Registration Request**

---

## 📋 ข้อมูลแบบฟอร์ม

| รายการ | รายละเอียด |
|--------|------------|
| รหัสแบบฟอร์ม | 20 |
| ชื่อ (ไทย) | คำร้องขอลงทะเบียนเรียนเพิ่ม |
| ชื่อ (อังกฤษ) | Request for Add Registration |
| ไฟล์ PDF | `20 คำร้องขอลงทะเบียนเรียนเพิ่ม (Add Registration).pdf` |
| Flow Diagram | `Registrar-20.jpg` |

---

## 🔍 Fields ที่ต้อง Extract ด้วย OCR

### ส่วนที่ 1: ข้อมูลนิสิต
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| ชื่อ-นามสกุล | Text | นายสมชาย ใจดี | อาจเป็นลายมือ |
| รหัสนิสิต | Text | 64xxxxxxxx | 10 หลัก |
| คณะ | Text | วิศวกรรมศาสตร์ | |
| สาขาวิชา | Text | วิศวกรรมคอมพิวเตอร์ | |
| ชั้นปี | Number | 3 | |
| เบอร์โทรศัพท์ | Text | 08x-xxx-xxxx | |

### ส่วนที่ 2: รายวิชาที่ขอลงทะเบียนเพิ่ม (Dynamic - หลายรายการ)
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| ลำดับ | Number | 1, 2, 3... | |
| รหัสวิชา | Text | 01418xxx | 8 หลัก |
| ชื่อวิชา | Text | Computer Programming | |
| หน่วยกิต | Number | 3 | |
| Section | Text | 1, 2, 801... | |
| วัน-เวลาเรียน | Text | จ. 09:00-12:00 | |
| อาจารย์ผู้สอน | Text | ดร.สมศรี | ⚠️ ต้อง map กับ database |

### ส่วนที่ 3: เหตุผล
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| เหตุผลที่ขอลงเพิ่ม | Text | ลงไม่ทันช่วงลงทะเบียน | Free text |

### ส่วนที่ 4: ลายเซ็น
| Field | Type | หมายเหตุ |
|-------|------|----------|
| ลายเซ็นนิสิต | Image | ตรวจว่ามีหรือไม่ |
| วันที่ | Date | dd/mm/yyyy |

---

## 🔄 Flow การอนุมัติ

```
┌─────────────────┐
│   นิสิตยื่นคำร้อง   │
└────────┬────────┘
         ▼
┌─────────────────┐
│  อาจารย์ที่ปรึกษา   │
│    (อนุมัติ)      │
└────────┬────────┘
         ▼
┌─────────────────────────────────────┐
│   อาจารย์ประจำวิชา (แต่ละวิชา)        │
│   ⚠️ Dynamic: ส่งแยกตามจำนวนวิชา      │
│   - วิชา A → อ.A                     │
│   - วิชา B → อ.B                     │
│   - วิชา C → อ.C                     │
└────────┬────────────────────────────┘
         ▼ (รอครบทุกวิชา)
┌─────────────────┐
│  นักวิชาการคณะ    │
│   (ตรวจสอบ)     │
└────────┬────────┘
         ▼
┌─────────────────┐
│     คณบดี       │
│   (อนุมัติ)      │
└────────┬────────┘
         ▼
┌─────────────────┐
│  งานทะเบียน      │
│ (ดำเนินการลงทะเบียน) │
└─────────────────┘
```

### ลำดับผู้อนุมัติ
| ลำดับ | ผู้อนุมัติ | Action | Notification |
|-------|-----------|--------|--------------|
| 1 | อาจารย์ที่ปรึกษา | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 2 | อาจารย์ประจำวิชา (ทุกวิชา) | อนุมัติ/ไม่อนุมัติ แต่ละวิชา | Email/Teams |
| 3 | นักวิชาการประจำคณะ | ตรวจสอบความถูกต้อง | Email/Teams |
| 4 | คณบดี | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 5 | งานทะเบียน | ดำเนินการลงทะเบียนในระบบ | Email แจ้งนิสิต |

---

## ⚠️ ความซับซ้อน: Dynamic Routing

### ปัญหา
- แต่ละคำร้องมีจำนวนวิชาไม่เท่ากัน (1-5+ วิชา)
- ต้องส่งให้อาจารย์ประจำวิชาแต่ละคนแยกกัน
- ต้องรอจนกว่าอาจารย์ทุกท่านอนุมัติครบ

### วิธีแก้ไข
1. **สร้าง Lookup Table**: mapping รหัสวิชา → Email อาจารย์
2. **Loop ใน Power Automate**: วนส่งทีละวิชา
3. **Track Status**: บันทึกสถานะแต่ละวิชาแยกกัน
4. **Parallel Approval**: รอจนครบทุกวิชา

---

## ⚠️ กรณีไม่อนุมัติ

| สถานะ | Action |
|-------|--------|
| อาจารย์ที่ปรึกษาไม่อนุมัติ | ส่งกลับนิสิตพร้อมเหตุผล |
| อาจารย์ประจำวิชาไม่อนุมัติ | ลบวิชานั้นออก, ดำเนินการต่อวิชาอื่น |
| คณบดีไม่อนุมัติ | ส่งกลับนิสิตพร้อมเหตุผล |

---

## 🛠️ Power Automate Flow Design

### Trigger
- เมื่อมีข้อมูลใหม่ใน SharePoint List "Form20_AddRegistration"

### Actions
1. ดึงไฟล์ PDF จาก attachment
2. เรียก OCR API → รับ JSON กลับ
3. Parse รายวิชา (array)
4. บันทึกข้อมูลลง List
5. ส่ง Email ให้อาจารย์ที่ปรึกษา
6. รอการอนุมัติ (Approval Action)
7. **Loop แต่ละวิชา**:
   - Lookup Email อาจารย์ประจำวิชา
   - ส่ง Approval Request
   - บันทึก Response
8. ตรวจสอบว่าครบทุกวิชา
9. ส่งให้นักวิชาการ → คณบดี
10. Update สถานะใน List
11. แจ้งนิสิตเมื่อเสร็จสิ้น

---

## 📊 SharePoint List Schema

### List 1: Form20_AddRegistration (Main)
| Column Name | Type | Required |
|-------------|------|----------|
| StudentName | Single line of text | Yes |
| StudentID | Single line of text | Yes |
| Faculty | Choice | Yes |
| Department | Single line of text | Yes |
| AdvisorEmail | Person | Yes |
| Reason | Multiple lines of text | Yes |
| Status | Choice | Yes |
| SubmitDate | Date | Yes |
| Attachment | Attachments | Yes |

### List 2: Form20_Courses (รายวิชา - 1:N relationship)
| Column Name | Type | Required |
|-------------|------|----------|
| RequestID | Lookup → Form20_Main | Yes |
| CourseCode | Single line of text | Yes |
| CourseName | Single line of text | Yes |
| Credits | Number | Yes |
| Section | Single line of text | Yes |
| InstructorEmail | Person | Yes |
| ApprovalStatus | Choice | Yes |
| ApprovalDate | Date | No |
| ApprovalComment | Multiple lines of text | No |

### List 3: Course_Instructor_Mapping (Lookup Table)
| Column Name | Type |
|-------------|------|
| CourseCode | Single line of text |
| InstructorName | Single line of text |
| InstructorEmail | Person |
| Department | Single line of text |
