'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { API_URL } from '@/lib/api'

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
    queryKey: ['memory-facts'],
    queryFn: () => fetch(`${API_URL}/api/memory/facts`).then(r => r.json()),
  })
}

export function useDeleteFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      fetch(`${API_URL}/api/memory/facts/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memory-facts'] }),
  })
}

export function useVerifyFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (f: UserFact) =>
      fetch(`${API_URL}/api/memory/facts/${f.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fact: f.fact,
          category: f.category,
          importance: f.importance,
          topics: f.topics,
          verifiedByUser: true,
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['memory-facts'] }),
  })
}
