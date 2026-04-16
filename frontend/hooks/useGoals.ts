import { useQuery } from '@tanstack/react-query'
import { Goal } from '@/types'
import { API_URL } from '@/lib/api'

export function useGoals() {
  return useQuery<Goal[]>({
    queryKey: ['goals'],
    queryFn: () => fetch(`${API_URL}/api/goals`).then(r => r.json()),
  })
}
