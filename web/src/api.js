// Small helpers for calling the Moneypenny API.
// Both throw an Error with the server's message when a request fails.

async function readReply(response) {
  if (response.ok) {
    return response.json()
  }
  let message = response.statusText
  try {
    const body = await response.json()
    if (body.detail) {
      message = body.detail
    }
  } catch (error) {
    // the error reply wasn't JSON; keep the status text
  }
  throw new Error(message)
}

export async function getJson(path) {
  const response = await fetch('/api' + path)
  return readReply(response)
}

export async function postJson(path, body) {
  const response = await fetch('/api' + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  })
  return readReply(response)
}
