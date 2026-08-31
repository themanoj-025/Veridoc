/** Dashboard handler hooks — extracted from page.tsx for readability. */

'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/authStore'
import {
  useDocuments,
  useConversations,
  useCreateConversation,
  useUploadDocument,
} from '@/hooks'
import { apiClient } from '@/lib/api'

export interface DashboardHandlers {
  handleNewConversation: () => Promise<void>
  handleUpload: (e: React.FormEvent<HTMLFormElement>) => Promise<void>
  handleFullTextSearch: (query: string) => Promise<void>
  handleDeleteAccount: () => Promise<void>
  handleLogout: () => void
}

export function useDashboardHandlers(params: {
  setSelectedDocId: React.Dispatch<React.SetStateAction<string | null>>
  setConversationId: React.Dispatch<React.SetStateAction<string | null>>
  setShowUploadModal: React.Dispatch<React.SetStateAction<boolean>>
  setUploading: React.Dispatch<React.SetStateAction<boolean>>
  setFullTextResults: React.Dispatch<React.SetStateAction<unknown[] | null>>
  setShowDeleteConfirm: React.Dispatch<React.SetStateAction<boolean>>
  setDeletingAccount: React.Dispatch<React.SetStateAction<boolean>>
  conversationId: string | null
  createConvMutation: ReturnType<typeof useCreateConversation>
  uploadMutation: ReturnType<typeof useUploadDocument>
}): DashboardHandlers {
