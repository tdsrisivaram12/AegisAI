import { Bell, Check, Trash2 } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { notificationsApi, type NotificationItem } from '../services/api'

/**
 * Notifications page — full list of in-app events.
 *
 * Backed by GET /api/v1/notifications, POST /api/v1/notifications/read and
 * DELETE /api/v1/notifications/{id}.
 */

export default function Notifications() {
  const queryClient = useQueryClient()

  const { data: notifications = [], isLoading } = useQuery<NotificationItem[]>({
    queryKey: ['notifications', 'all'],
    queryFn: () => notificationsApi.list(false),
    refetchInterval: 60_000,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
  }

  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => {
      refresh()
      toast.success('Notifications marked as read')
    },
    onError: () => toast.error('Could not mark notifications as read'),
  })

  const deleteMutation = useMutation({
    mutationFn: notificationsApi.remove,
    onSuccess: () => {
      refresh()
      toast.success('Notification deleted')
    },
    onError: () => toast.error('Could not delete notification'),
  })

  const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Notifications</h1>
          <p className="text-gray-600">Your recent compliance and system events</p>
        </div>
        <button
          type="button"
          onClick={() => markReadMutation.mutate(unreadIds)}
          disabled={unreadIds.length === 0 || markReadMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg border border-gray-200 disabled:opacity-50 disabled:hover:bg-transparent"
        >
          <Check className="w-4 h-4" />
          Mark all read
        </button>
      </div>

      {/* Notification list */}
      {isLoading ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200 text-gray-500">
          Loading notifications…
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
          <Bell className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <h3 className="text-lg font-medium text-gray-900">No notifications</h3>
          <p className="text-gray-500 mt-1">You're all caught up.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`bg-white rounded-xl border p-4 flex items-start gap-4 ${
                n.is_read ? 'border-gray-200' : 'border-primary-200 bg-primary-50'
              }`}
            >
              <div
                className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${
                  n.is_read ? 'bg-gray-300' : 'bg-primary-600'
                }`}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 text-sm">{n.title}</p>
                <p className="text-gray-600 text-sm mt-0.5">{n.message}</p>
                <p className="text-gray-400 text-xs mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
              <button
                type="button"
                onClick={() => deleteMutation.mutate(n.id)}
                disabled={deleteMutation.isPending}
                aria-label="Delete notification"
                className="p-1 text-gray-400 hover:text-red-500 rounded disabled:opacity-50"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
