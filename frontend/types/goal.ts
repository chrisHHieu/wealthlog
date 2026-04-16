export interface Goal {
  id: string
  name: string
  type?: string
  targetAmount: number
  currentAmount: number
  deadline?: string
  icon: string
  color: string
  description?: string
  isCompleted?: boolean
}
