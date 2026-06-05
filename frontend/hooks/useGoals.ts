import { useQuery } from '@tanstack/react-query'
import { Goal } from '@/types'
import { apiGet, queryKeys } from '@/lib/api'

export function useGoals() {
  return useQuery<Goal[]>({
    queryKey: queryKeys.goals,
    queryFn: () => apiGet<Goal[]>('/api/goals'),
  })
}
