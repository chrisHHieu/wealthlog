import { z } from 'zod'

export const transactionSchema = z.object({
  type: z.enum(['income', 'expense', 'transfer']),
  amount: z.number().positive('Số tiền phải lớn hơn 0'),
  accountId: z.string().min(1, 'Vui lòng chọn tài khoản'),
  toAccountId: z.string().optional(),
  categoryId: z.string().optional(),
  description: z.string().min(1, 'Vui lòng nhập mô tả'),
  note: z.string().optional(),
  tags: z.array(z.string()).optional(),
  date: z.string().min(1, 'Vui lòng chọn ngày'),
})

export const accountSchema = z.object({
  name: z.string().min(1, 'Vui lòng nhập tên tài khoản'),
  type: z.enum(['cash', 'bank', 'ewallet', 'investment', 'savings', 'debt']),
  balance: z.number().default(0),
  color: z.string().default('#00C896'),
  icon: z.string().default('💳'),
  description: z.string().optional(),
})

export const budgetSchema = z.object({
  categoryId: z.string().min(1, 'Vui lòng chọn danh mục'),
  amount: z.number().positive('Ngân sách phải lớn hơn 0'),
  month: z.string().min(1, 'Vui lòng chọn tháng'),
})

export const goalSchema = z.object({
  name: z.string().min(1, 'Vui lòng nhập tên mục tiêu'),
  type: z.enum(['emergency', 'savings', 'purchase', 'investment', 'debt', 'custom']),
  targetAmount: z.number().positive('Mục tiêu phải lớn hơn 0'),
  currentAmount: z.number().default(0),
  deadline: z.string().optional(),
  icon: z.string().default('🎯'),
  color: z.string().default('#00C896'),
  description: z.string().optional(),
})

export const investmentSchema = z.object({
  name: z.string().min(1, 'Vui lòng nhập tên tài sản'),
  type: z.enum(['stock', 'etf', 'gold', 'realestate', 'savings', 'crypto', 'other']),
  symbol: z.string().optional(),
  quantity: z.number().positive('Số lượng phải lớn hơn 0'),
  buyPrice: z.number().positive('Giá mua phải lớn hơn 0'),
  currentPrice: z.number().positive('Giá hiện tại phải lớn hơn 0'),
  buyDate: z.string().min(1, 'Vui lòng chọn ngày mua'),
  accountId: z.string().optional(),
  note: z.string().optional(),
})

export const categorySchema = z.object({
  name: z.string().min(1, 'Vui lòng nhập tên danh mục'),
  type: z.enum(['income', 'expense', 'both']),
  icon: z.string().default('📦'),
  color: z.string().default('#6366f1'),
})

export type TransactionFormData = z.infer<typeof transactionSchema>
export type AccountFormData = z.infer<typeof accountSchema>
export type BudgetFormData = z.infer<typeof budgetSchema>
export type GoalFormData = z.infer<typeof goalSchema>
export type InvestmentFormData = z.infer<typeof investmentSchema>
export type CategoryFormData = z.infer<typeof categorySchema>
