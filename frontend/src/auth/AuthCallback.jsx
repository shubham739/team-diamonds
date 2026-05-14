import { useEffect, useRef, useState } from 'react';
import { userManager } from './authConfig';

function AuthCallback() {
  const [user, setUser] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const callbackHandled = useRef(false);

  useEffect(() => {
    if (callbackHandled.current) {
      return;
    }
    callbackHandled.current = true;

    userManager.signinRedirectCallback()
      .then((callbackUser) => {
        setUser(callbackUser);
        setTimeout(() => {
          window.location.href = '/';
        }, 1200);
      })
      .catch(async (error) => {
        const message = error instanceof Error ? error.message : String(error);

        // In dev, React StrictMode can attempt callback processing twice.
        if (message.includes('No matching state found in storage')) {
          const existingUser = await userManager.getUser();
          if (existingUser) {
            setUser(existingUser);
            window.location.href = '/';
            return;
          }
        }

        console.error('Login failed:', error);
        setErrorMessage(message);
      });
  }, []);

  if (user) {
    return <div>Login successful. Redirecting...</div>;
  }

  if (errorMessage) {
    return <div>Login failed: {errorMessage}</div>;
  }

  return <div>Logging you in...</div>;
}

export default AuthCallback;