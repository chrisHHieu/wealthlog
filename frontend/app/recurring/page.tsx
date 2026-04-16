import { AppLayout } from '@/components/layout/AppLayout'
import { RecurringPage } from '@/components/recurring/RecurringPage'

export const metadata = {
  title: 'Giao dịch định kỳ | WealthLog',
}

export default function Recurring() {
  return (
    <AppLayout>
      <RecurringPage />
    </AppLayout>
  )
}
