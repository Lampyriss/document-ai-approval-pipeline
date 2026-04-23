# 📄 SPEC: แบบ 4 - ขอลงทะเบียนเรียนควบ
**Continuing Course with Prerequisite**

---

## 📋 ข้อมูลแบบฟอร์ม

| รายการ | รายละเอียด |
|--------|------------|
| รหัสแบบฟอร์ม | 4 |
| ชื่อ (ไทย) | คำร้องขอลงทะเบียนเรียนควบ |
| ชื่อ (อังกฤษ) | Request for Continuing Course with Prerequisite |
| ไฟล์ PDF | `4 ขอลงทะเบียนเรียนควบ(Continuing course with prerequistie)-Revised.pdf` |
| Flow Diagram | `Registrar-4.jpg` |

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

### ส่วนที่ 2: วิชาบังคับก่อน (Prerequisite)
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| รหัสวิชา | Text | 01418111 | วิชาที่ต้องเรียนก่อน |
| ชื่อวิชา | Text | Introduction to Computer Science | |
| หน่วยกิต | Number | 3 | |

### ส่วนที่ 3: วิชาต่อเนื่อง (ที่ต้องการลงพร้อมกัน)
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| รหัสวิชา | Text | 01418112 | วิชาที่ต้องการเรียนควบ |
| ชื่อวิชา | Text | Computer Programming | |
| หน่วยกิต | Number | 3 | |
| Section | Text | 1 | |

### ส่วนที่ 4: เหตุผล
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| เหตุผลที่ขอเรียนควบ | Text | จะสำเร็จการศึกษาภาคนี้ | Free text |

### ส่วนที่ 5: ลายเซ็น
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
│   อาจารย์ประจำวิชา (2 วิชา)          │
│   ⚠️ ส่ง 2 ฝั่ง:                     │
│   - วิชาบังคับก่อน → อ.A             │
│   - วิชาต่อเนื่อง → อ.B              │
└────────┬────────────────────────────┘
         ▼ (รอครบทั้ง 2 วิชา)
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
│ (อนุมัติการลงทะเบียน) │
└─────────────────┘
```

### ลำดับผู้อนุมัติ
| ลำดับ | ผู้อนุมัติ | Action | Notification |
|-------|-----------|--------|--------------|
| 1 | อาจารย์ที่ปรึกษา | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 2a | อาจารย์ประจำวิชาบังคับก่อน | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 2b | อาจารย์ประจำวิชาต่อเนื่อง | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 3 | นักวิชาการประจำคณะ | ตรวจสอบความถูกต้อง | Email/Teams |
| 4 | คณบดี | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 5 | งานทะเบียน | ดำเนินการในระบบ | Email แจ้งนิสิต |

---

## ⚠️ ความแตกต่างจากแบบ 20

| แบบ 4 (เรียนควบ) | แบบ 20 (ลงเพิ่ม) |
|-----------------|-----------------|
| มี 2 วิชาเสมอ (บังคับก่อน + ต่อเนื่อง) | จำนวนวิชาไม่จำกัด |
| ต้องส่ง 2 อาจารย์พร้อมกัน | ส่งตามจำนวนวิชา |
| Logic ง่ายกว่า | ต้อง loop |

---

## ⚠️ กรณีไม่อนุมัติ

| สถานะ | Action |
|-------|--------|
| อาจารย์ที่ปรึกษาไม่อนุมัติ | ส่งกลับนิสิตพร้อมเหตุผล |
| อาจารย์ประจำวิชาไม่อนุมัติ (อย่างใดอย่างหนึ่ง) | ยกเลิกคำร้องทั้งหมด |
| คณบดีไม่อนุมัติ | ส่งกลับนิสิตพร้อมเหตุผล |

---

## 🛠️ Power Automate Flow Design

### Trigger
- เมื่อมีข้อมูลใหม่ใน SharePoint List "Form4_Prerequisite"

### Actions
1. ดึงไฟล์ PDF จาก attachment
2. เรียก OCR API → รับ JSON กลับ
3. บันทึกข้อมูลลง List
4. ส่ง Email ให้อาจารย์ที่ปรึกษา
5. รอการอนุมัติ (Approval Action)
6. **Parallel Branch**:
   - Branch A: ส่งให้ อ.วิชาบังคับก่อน
   - Branch B: ส่งให้ อ.วิชาต่อเนื่อง
7. รอจนครบทั้ง 2 ฝั่ง
8. ตรวจสอบ: ถ้าอนุมัติทั้งคู่ → ดำเนินการต่อ
9. ส่งให้นักวิชาการ → คณบดี
10. Update สถานะใน List
11. แจ้งนิสิตเมื่อเสร็จสิ้น

---

## 📊 SharePoint List Schema

### List 1: Form4_Prerequisite (Main)
| Column Name | Type | Required |
|-------------|------|----------|
| StudentName | Single line of text | Yes |
| StudentID | Single line of text | Yes |
| Faculty | Choice | Yes |
| Department | Single line of text | Yes |
| AdvisorEmail | Person | Yes |
| Reason | Multiple lines of text | Yes |
| PrereqCourseCode | Single line of text | Yes |
| PrereqCourseName | Single line of text | Yes |
| PrereqCredits | Number | Yes |
| PrereqInstructor | Person | Yes |
| PrereqApproval | Choice | No |
| ContinuingCourseCode | Single line of text | Yes |
| ContinuingCourseName | Single line of text | Yes |
| ContinuingCredits | Number | Yes |
| ContinuingSection | Single line of text | Yes |
| ContinuingInstructor | Person | Yes |
| ContinuingApproval | Choice | No |
| Status | Choice | Yes |
| SubmitDate | Date | Yes |
| Attachment | Attachments | Yes |
