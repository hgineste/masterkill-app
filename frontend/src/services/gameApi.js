import apiClient from '@/services/apiClient'

export async function uploadScreenshot (gameId, file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await apiClient.post(
    `/games/${gameId}/upload-screenshot/`,
    fd,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return data.players          // [{gamertag,kills,revives}]
}
