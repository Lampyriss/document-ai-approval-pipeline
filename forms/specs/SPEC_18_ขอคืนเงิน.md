# 📄 SPEC: แบบ 18 - ขอคืนเงินค่าธรรมเนียมการศึกษา
**Refund of Tuition Fee**

---

## 📋 ข้อมูลแบบฟอร์ม

| รายการ | รายละเอียด |
|--------|------------|
| รหัสแบบฟอร์ม | 18 |
| ชื่อ (ไทย) | คำร้องขอคืนเงินค่าธรรมเนียมการศึกษา |
| ชื่อ (อังกฤษ) | Request for Refund of Tuition Fee |
| ไฟล์ PDF | `18 ขอคืนเงิน (Refund of tuition fee)-Revised.pdf` |
| Flow Diagram | `Registrar-18.jpg` |

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
| Email | Text | xxx@ku.th | |

### ส่วนที่ 2: รายละเอียดการขอคืนเงิน
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| ภาคการศึกษา | Text | ต้น/ปลาย/ฤดูร้อน | |
| ปีการศึกษา | Text | 2567 | |
| เหตุผลการขอคืนเงิน | Text | ลาออก/พ้นสภาพ/อื่นๆ | Checkbox + ระบุ |
| จำนวนเงินที่ขอคืน | Number | 25,000 | บาท |

### ส่วนที่ 3: ข้อมูลบัญชี
| Field | Type | ตัวอย่าง | หมายเหตุ |
|-------|------|----------|----------|
| ชื่อบัญชี | Text | นายสมชาย ใจดี | |
| ธนาคาร | Text | กสิกรไทย | |
| เลขบัญชี | Text | xxx-x-xxxxx-x | |

### ส่วนที่ 4: ลายเซ็น
| Field | Type | หมายเหตุ |
|-------|------|----------|
| ลายเซ็นนิสิต | Image/Checkbox | ตรวจว่ามีหรือไม่ |
| วันที่ | Date | dd/mm/yyyy |

---

## 🔄 Flow การอนุมัติ

```
┌─────────────────┐
│   นิสิตยื่นคำร้อง   │
└────────┬────────┘
         ▼
┌─────────────────┐
│  นักวิชาการตรวจสอบ  │
│   (ความถูกต้อง)    │
└────────┬────────┘
         ▼
┌─────────────────┐
│   หัวหน้างาน     │
│  ทะเบียนนิสิต    │
└────────┬────────┘
         ▼
┌─────────────────┐
│  ผู้อำนวยการกอง   │
│   บริหารวิชาการ   │
└────────┬────────┘
         ▼
┌─────────────────┐
│   งานการเงิน     │
│  (ดำเนินการคืนเงิน) │
└─────────────────┘
```

### ลำดับผู้อนุมัติ
| ลำดับ | ผู้อนุมัติ | Action | Notification |
|-------|-----------|--------|--------------|
| 1 | นักวิชาการประจำคณะ | ตรวจสอบความถูกต้อง | Email/Teams |
| 2 | หัวหน้างานทะเบียนนิสิต | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 3 | ผู้อำนวยการกองบริหารวิชาการ | อนุมัติ/ไม่อนุมัติ | Email/Teams |
| 4 | งานการเงิน | ดำเนินการโอนเงิน | Email แจ้งนิสิต |

---

## ⚠️ กรณีไม่อนุมัติ

| สถานะ | Action |
|-------|--------|
| ไม่อนุมัติ | ส่งกลับนิสิตพร้อมเหตุผล |
| เอกสารไม่ครบ | แจ้งให้ส่งเอกสารเพิ่มเติม |

---

## 🛠️ Power Automate Flow Design

### Trigger
- เมื่อมีข้อมูลใหม่ใน SharePoint List "Form18_Refund"

### Actions
1. ดึงไฟล์ PDF จาก attachment
2. เรียก OCR API → รับ JSON กลับ
3. บันทึกข้อมูลลง List
4. ส่ง Email ให้นักวิชาการ
5. รอการอนุมัติ (Approval Action)
6. ส่งต่อตามลำดับ
7. Update สถานะใน List
8. แจ้งนิสิตเมื่อเสร็จสิ้น

---

## 📊 SharePoint List Schema

| Column Name | Type | Required |
|-------------|------|----------|
| StudentName | Single line of text | Yes |
| StudentID | Single line of text | Yes |
| Faculty | Choice | Yes |
| Department | Single line of text | Yes |
| Semester | Choice | Yes |
| AcademicYear | Single line of text | Yes |
| RefundReason | Multiple lines of text | Yes |
| RefundAmount | Number | Yes |
| BankName | Single line of text | Yes |
| BankAccount | Single line of text | Yes |
| Status | Choice | Yes |
| CurrentApprover | Person | No |
| SubmitDate | Date | Yes |
| Attachment | Attachments | Yes |
