# คลังความรู้ส่วนตัว (Personal Knowledge Base)

เว็บโน้ต/คู่มือส่วนตัว สร้างด้วย [MkDocs Material](https://squidfunk.github.io/mkdocs-material/)
เผยแพร่อัตโนมัติบน **GitHub Pages** — ฟรี และแก้ไขผ่านเว็บ GitHub ได้จากทุกเครื่อง
(รวมถึงคอมที่ติดตั้งโปรแกรมไม่ได้)

🌐 **เว็บ:** https://ttharkesm-admin01.github.io/AI-Agent/

## วิธีทำงาน

1. โน้ตทุกอันคือไฟล์ Markdown ใน `docs/`
2. แก้ไข/เพิ่มไฟล์ผ่านเว็บ GitHub แล้ว commit เข้า `main`
3. GitHub Actions (`.github/workflows/deploy.yml`) build แล้ว deploy ให้อัตโนมัติ
   ภายใน 1–2 นาที

รายละเอียดวิธีเพิ่มโน้ต หมวดหมู่ และ Markdown ที่ใช้บ่อย อยู่ในหน้า
[วิธีใช้งาน](docs/guide/add-note.md) ของตัวเว็บเอง

## โครงสร้าง

```
mkdocs.yml            # ตั้งค่าเว็บ + เมนู (nav)
requirements.txt      # mkdocs-material
docs/
  index.md            # หน้าแรก
  guide/add-note.md   # คู่มือการใช้งาน
  work/               # หมวด: งาน
  learning/           # หมวด: เรียนรู้
.github/workflows/deploy.yml   # build + deploy GitHub Pages อัตโนมัติ
.devcontainer/        # เปิด Codespace เพื่อ preview เว็บสด ๆ (ถ้าต้องการ)
```

## Preview ก่อนเผยแพร่ (ไม่บังคับ)

เปิด Codespace (**Code → Codespaces → Create codespace**) แล้ว:

```bash
mkdocs serve -a 0.0.0.0:8000
```

## หมายเหตุ

- GitHub Pages ฟรีสำหรับ repo **public** (repo private ต้องใช้แพลน Pro/Team)
- โปรเจคก่อนหน้าใน repo นี้ (AI-Agent CLI) ยังอยู่ใน git history —
  ดูได้ที่ commit `9902ee7`/`9126e45` หรือ PR #1
