import { useEffect, useState } from 'react'

export default function JiraCallback({ onConnected }) {
  const [status, setStatus] = useState('Connecting Jira...')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const accessToken = params.get('access_token')
    const userId = params.get('user_id')

    if (accessToken && userId) {
        localStorage.setItem('jira_access_token', accessToken)
        localStorage.setItem('jira_user_id', userId)
        onConnected?.() 
        setStatus('Jira connected! Redirecting...')
        setTimeout(() => {
        window.location.href = '/'
      }, 1500)
    } else {
      setStatus('Jira connection failed. Please try again.')
    }
  }, [])

  return (
    <div>
      <p>{status}</p>
    </div>
  )
}
