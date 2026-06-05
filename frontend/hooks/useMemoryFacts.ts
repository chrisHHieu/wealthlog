'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiDelete, apiGet, apiJson, queryKeys } from '@/lib/api'

export interface UserFact {
  id: string
  fact: string
  category: string
  importance: number
  topics: string[]
  verifiedByUser: boolean
  expiresAt: string | null
  accessCount: number
  lastAccessedAt: string | null
  createdAt: string
  updatedAt: string
}

export function useMemoryFacts() {
  return useQuery<UserFact[]>({
    queryKey: queryKeys.memoryFacts,
    queryFn: () => apiGet<UserFact[]>('/api/memory/facts'),
  })
}

export function useDeleteFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiDelete(`/api/memory/facts/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.memoryFacts }),
  })
}

export function useVerifyFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (f: UserFact) =>
      apiJson(`/api/memory/facts/${f.id}`, {
        method: 'PUT',
        body: {
          fact: f.fact,
          category: f.category,
          importance: f.importance,
          topics: f.topics,
          verifiedByUser: true,
        },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.memoryFacts }),
  })
}
