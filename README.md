Đây là prompt được viết lại, tối ưu cho Claude Code để build trực tiếp — bao gồm tech stack đầy đủ và loại bỏ yêu cầu về tablet/mobile như bạn muốn:

---

# Personal Finance Manager — Full-Stack Web App

## 🎯 MỤC TIÊU DỰ ÁN

Xây dựng ứng dụng web quản lý tài chính cá nhân (Personal Finance Manager) — dùng riêng cho một người, không phải sản phẩm thương mại. Thiết kế đầy đủ, chuyên nghiệp, hiện đại theo phong cách **"Luxury Fintech"**.

---

## 🛠️ TECH STACK

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS + CSS Variables cho theming dark/light
- **UI Components**: shadcn/ui (làm base, customize lại toàn bộ visual)
- **Charts**: Recharts hoặc Tremor cho line chart, donut, bar, waterfall
- **Animations**: Framer Motion cho page transitions, số đếm lên, chart vẽ dần
- **Icons**: Lucide React + custom emoji icons cho danh mục
- **Date handling**: date-fns
- **Form & Validation**: React Hook Form + Zod
- **State management**: Zustand (client state) + TanStack Query (server state / data fetching)
- **Fonts**: Instrument Serif (display, dùng cho số liệu lớn) + Geist Sans (body text) — load qua `next/font`

### Backend
- **Runtime**: Node.js với Next.js API Routes (App Router — Route Handlers)
- **Database**: PostgreSQL (production) / SQLite via Turso (local dev — lightweight, zero config)
- **ORM**: Drizzle ORM (type-safe, nhẹ hơn Prisma, phù hợp dự án cá nhân)
- **Auth**: NextAuth.js v5 (hoặc bỏ auth nếu dùng local — chỉ cần 1 tài khoản)
- **File Export**: `exceljs` cho Excel export, `@react-pdf/renderer` cho PDF
- **CSV Import**: `papaparse`

### Dev & Tooling
- **Package manager**: pnpm
- **Linting**: ESLint + Prettier
- **Database migrations**: Drizzle Kit

---

## 🗂️ CẤU TRÚC THƯ MỤC GỢI Ý

```
/app
  /(dashboard)/page.tsx          → Dashboard
  /transactions/page.tsx         → Giao dịch
  /accounts/page.tsx             → Tài khoản
  /budget/page.tsx               → Ngân sách
  /goals/page.tsx                → Mục tiêu
  /investments/page.tsx          → Đầu tư
  /reports/page.tsx              → Báo cáo
  /settings/page.tsx             → Cài đặt
  /api/...                       → Route Handlers

/components
  /ui/                           → shadcn base components
  /dashboard/                    → Dashboard-specific components
  /transactions/                 → Transaction form, list, filters
  /charts/                       → Recharts wrappers
  /layout/                       → Sidebar, Header, FAB

/lib
  /db/schema.ts                  → Drizzle schema
  /db/queries.ts                 → Typed queries
  /utils/                        → Format tiền VND, date helpers
  /validations/                  → Zod schemas

/hooks/                          → Custom React hooks
/store/                          → Zustand stores
```

---

## 🎨 ĐỊNH HƯỚNG THẨM MỸ

**Phong cách**: "Luxury Fintech" — tối giản nhưng tinh tế, sang trọng, dense data nhưng không rối mắt. Cảm giác như Bloomberg Terminal được thiết kế lại cho người dùng thông thường.

**Colors** (dùng CSS variables, support dark/light toggle):
- Nền chính dark mode: `#0F0F14`
- Accent dương: Emerald `#00C896`
- Accent âm: Rose `#FF4D6D`
- Surface cards: `rgba(255,255,255,0.04)` với backdrop-blur

**Typography**:
- Display numbers (Net Worth, KPI lớn): Instrument Serif, size 48-72px
- Body/UI text: Geist Sans

**Micro-animations** (implement bằng Framer Motion):
- Số liệu đếm lên khi component mount (counter animation)
- Chart vẽ dần từ trái sang phải
- Card hover: subtle scale + glow effect
- Page transition: fade + slide nhẹ
- Loading: skeleton shimmer thay vì spinner

---

## 🗺️ CÁC TRANG CẦN BUILD

### 1. DASHBOARD

**Header**: Lời chào cá nhân hóa ("Chào buổi sáng, [Tên] ☀️") + ngày hiện tại + notification icon + avatar.

**Hero section — "Sức khỏe tài chính tháng này"**:
- Net Worth hiển thị cực to, font Instrument Serif, animation đếm số khi load
- So sánh với tháng trước: `+X.XXX.XXX đ (+12.3%)` với mũi tên màu
- 3 KPI card ngang: [Tổng thu nhập] [Tổng chi tiêu] [Tiết kiệm được]

**Biểu đồ chính**: Line chart thu vs chi 6 tháng (có toggle: 3T / 6T / 12T). Hover tooltip chi tiết.

**Donut chart**: Chi tiêu theo danh mục, click vào từng mảnh xem chi tiết.

**Giao dịch gần nhất**: 5–7 mục, link "Xem tất cả".

**Goals snapshot**: 2–3 goal card nhỏ với progress bar, % hoàn thành, deadline.

---

### 2. GIAO DỊCH (Transactions)

**Filter bar**: Search | Date range picker | Danh mục (multi-select) | Loại (Thu/Chi/Chuyển khoản) | Tài khoản.

**Danh sách**: Group theo ngày (header ngày + tổng thu/chi). Mỗi row: icon danh mục màu | tên | ghi chú | tag | tài khoản | số tiền (xanh/đỏ). Hover row → nút Edit | Delete. Click row → **side panel** chi tiết (không navigate).

**Form thêm/sửa** (Side drawer hoặc Modal):
- 3 tab: Thu / Chi / Chuyển khoản
- Số tiền: input lớn, hỗ trợ shorthand `1tr`, `500k`, `1.5m`
- Danh mục: icon grid picker
- Ngày: date picker, default hôm nay
- Tài khoản: dropdown
- Ghi chú + Tags tự do
- Nút: Lưu | Lưu & thêm tiếp

---

### 3. TÀI KHOẢN (Accounts)

Net Worth tổng + tổng nợ ở trên. Danh sách tài khoản dạng card, phân nhóm: Tiền mặt & Ngân hàng | Ví điện tử | Đầu tư | Tiết kiệm | Nợ/Vay. Mỗi card: logo/icon | tên | số dư | thay đổi tháng này. Click card → lịch sử giao dịch của tài khoản đó. Form thêm tài khoản: loại, tên, số dư ban đầu, màu & icon tuỳ chọn.

---

### 4. NGÂN SÁCH (Budget)

Header: "Tháng X/YYYY — Còn X ngày" + tổng ngân sách vs thực chi. Navigate qua lại giữa các tháng.

Danh sách theo danh mục: icon | tên | progress bar gradient (xanh <70% → vàng 70–90% → đỏ >90% → đỏ nháy khi vượt) | đã chi / ngân sách | % còn lại.

Stacked bar chart so sánh ngân sách vs thực chi từng danh mục. Nút "Thiết lập ngân sách tháng sau" — copy từ tháng này hoặc nhập mới.

---

### 5. MỤC TIÊU TÀI CHÍNH (Goals)

Header: tổng tiết kiệm đang theo đuổi + số mục tiêu active.

Card grid 2 cột. Mỗi card: tên mục tiêu | emoji/icon | circular progress bar lớn ở giữa (%) | số tiền hiện có / mục tiêu | deadline "Còn X tháng" | cần tiết kiệm thêm X/tháng | nút Thêm tiền | Sửa | Chi tiết.

Detail view: lịch sử thêm tiền (timeline) + dự báo đạt mục tiêu + gợi ý "Cần thêm X.XXX.XXX đ/tháng để đạt đúng hạn".

Loại mục tiêu có sẵn: Quỹ khẩn cấp | Tiết kiệm kỳ hạn | Mua sắm lớn | Quỹ đầu tư | Trả nợ | Custom.

---

### 6. ĐẦU TƯ (Investments)

Tổng giá trị đầu tư + tổng lãi/lỗ (số + %) + biểu đồ tăng trưởng theo thời gian.

Danh sách tài sản (manual input): Cổ phiếu | ETF/Chứng chỉ quỹ | Vàng | Bất động sản | Tiết kiệm có kỳ hạn (tính lãi tự động) | Crypto (tuỳ chọn).

Mỗi tài sản: % allocation (pie chart) | ROI | ngày mua / thời gian nắm giữ.

---

### 7. BÁO CÁO (Reports)

Bộ lọc: Tháng / Quý / Năm / Tùy chọn + Tài khoản.

Các báo cáo: Thu nhập vs Chi tiêu (bar chart song song) | Chi tiêu theo danh mục (donut + bảng, drill-down xem giao dịch) | Xu hướng tiết kiệm (line chart, highlight tháng tốt/tệ nhất) | Cash Flow (waterfall chart theo tuần) | Net Worth History (line chart từ ngày đầu dùng app, có milestone markers).

Export: PDF và Excel.

---

### 8. CÀI ĐẶT (Settings)

Thông tin cá nhân: tên, avatar, đồng tiền mặc định (VND). Quản lý danh mục: thêm/sửa/xóa + icon + màu. Giao diện: toggle Dark/Light mode, ngôn ngữ VI/EN. Dữ liệu: import CSV, export toàn bộ, xóa data. Về ứng dụng: phiên bản, changelog.

---

## 🧭 NAVIGATION (Desktop only)

**Sidebar trái — collapsible**:
- Logo / tên app ở trên
- Menu: Dashboard | Giao dịch | Tài khoản | Ngân sách | Mục tiêu | Đầu tư | Báo cáo
- Phần dưới sidebar: Cài đặt | Toggle dark/light

**Floating Action Button (FAB)**: Nút `+` nổi luôn visible trên mọi trang — mở form thêm giao dịch nhanh.

---

## 🔑 UX PATTERNS BẮT BUỘC

- **Empty states**: Minh họa SVG đơn giản + CTA rõ ràng (VD: "Bạn chưa có giao dịch nào. Thêm giao dịch đầu tiên →")
- **Loading**: Skeleton shimmer thay vì spinner
- **Undo xóa**: Toast "Đã xóa. Hoàn tác?" tồn tại 3 giây
- **Format tiền VND**: Luôn dùng `1.500.000 đ` (dấu chấm phân cách, chữ "đ" sau)
- **Highlight giao dịch mới**: Fade-in animation nhẹ sau khi thêm
- **Keyboard shortcuts** (desktop): `N` = new transaction, `/` = focus search
- **Confirm dialog** cho mọi action destructive (xóa tài khoản, xóa mục tiêu, xóa dữ liệu)
- **Side panel** thay navigate cho xem chi tiết giao dịch

---

## 📋 THỨ TỰ BUILD

Implement theo thứ tự sau:

1. Setup dự án: khởi tạo Next.js + Tailwind + shadcn/ui + Drizzle + Zustand + TanStack Query
2. Database schema + seed data mẫu
3. Layout chính: Sidebar + Header + FAB
4. **Dashboard** — full desktop
5. **Giao dịch** + form thêm/sửa
6. **Mục tiêu**
7. **Ngân sách**
8. **Tài khoản**
9. **Đầu tư**
10. **Báo cáo**
11. **Cài đặt**

---

Prompt này sẵn sàng để paste vào Claude Code. Một số lưu ý để dùng hiệu quả hơn:

Bạn nên bắt đầu với lệnh `claude` trong một thư mục trống, paste prompt trên, và để Claude Code tự khởi tạo toàn bộ project structure. Nếu muốn Claude Code tập trung vào từng phần thay vì build cả cùng lúc, bạn có thể thêm câu "Hãy bắt đầu với bước 1–3 trước, sau đó dừng lại và chờ tôi xác nhận" vào cuối prompt.

Về tech stack, lý do chọn **Drizzle + SQLite/Turso** thay vì Prisma + PostgreSQL là vì đây là app cá nhân — không cần infrastructure phức tạp, có thể chạy local hoàn toàn không tốn chi phí. Khi muốn deploy, chỉ cần migrate sang Turso (SQLite edge) hoặc Neon (PostgreSQL serverless) là xong.