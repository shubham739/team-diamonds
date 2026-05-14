// import { UserManager } from "oidc-client-ts";

// const cognitoAuthConfig = {
//     authority: "https://cognito-idp.us-east-2.amazonaws.com/us-east-2_KQ1PyAT4Z",
//     client_id: "5o5e53deluid97pmfk56767231",
//     redirect_uri: "http://localhost:3000/callback.html",
//     response_type: "code",
//     scope: "openid email profile"
// };

// // create a UserManager instance
// export const userManager = new UserManager({
//     ...cognitoAuthConfig,
// });

// export async function signOutRedirect () {
//     const clientId = "5o5e53deluid97pmfk56767231";
//     const logoutUri = "http://localhost:3000/";
//     const cognitoDomain = "https://team-diamonds.auth.us-east-2.amazoncognito.com";
//     window.location.href = `${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(logoutUri)}`;
// };