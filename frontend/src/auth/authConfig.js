import { UserManager, WebStorageStateStore } from "oidc-client-ts";

const cognitoDomain = import.meta.env.VITE_COGNITO_AUTHORITY_URL;
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID;

// These URLs must exactly match the values registered in the Cognito App Client.
const LOGOUT_URI = import.meta.env.VITE_MAIN_URI
const REDIRECT_URI = import.meta.env.VITE_MAIN_URI + "/callback";

const cognitoAuthConfig = {
    authority: cognitoDomain,
    client_id: clientId,
    redirect_uri: REDIRECT_URI,
    post_logout_redirect_uri: LOGOUT_URI,
    response_type: "code",
    scope: "openid email profile",
    metadata: {
        issuer: cognitoDomain,
        authorization_endpoint: `${cognitoDomain}/oauth2/authorize`,
        token_endpoint: `${cognitoDomain}/oauth2/token`,
        userinfo_endpoint: `${cognitoDomain}/oauth2/userInfo`,
        end_session_endpoint: `${cognitoDomain}/logout`,
    },
};

// Persist auth transaction state in localStorage so the /callback route can
// always find the matching state key regardless of page reloads or strict-mode re-renders.
const localStorageStore =
    typeof window !== "undefined" ? new WebStorageStateStore({ store: window.localStorage }) : undefined;

export const userManager = new UserManager({
    ...cognitoAuthConfig,
    userStore: localStorageStore,
    stateStore: localStorageStore,
});

export async function signOutRedirect() {
    await userManager.removeUser();
    window.location.href = LOGOUT_URI;
}
