import { api } from "./api";

// Base64Url to Uint8Array
function b64uDec(s: string): BufferSource {
  const b64 = s.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr as unknown as BufferSource;
}

// Uint8Array to Base64Url
function b64uEnc(buf: ArrayBuffer): string {
  const bin = String.fromCharCode(...new Uint8Array(buf));
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

export async function signupPasskey(username: string, policy?: any) {
  const opts = await api.auth.registerOpts(username);
  
  const publicKey: PublicKeyCredentialCreationOptions = {
    challenge: b64uDec(opts.challenge),
    rp: { name: opts.rp.name, id: opts.rp.id },
    user: {
      id: b64uDec(opts.user.id),
      name: opts.user.name,
      displayName: opts.user.displayName,
    },
    pubKeyCredParams: opts.pubKeyCredParams,
    authenticatorSelection: opts.authenticatorSelection,
    timeout: opts.timeout,
    attestation: opts.attestation as AttestationConveyancePreference,
  };

  const cred = await navigator.credentials.create({ publicKey }) as PublicKeyCredential;
  if (!cred) throw new Error("Passkey creation cancelled or failed");

  const response = cred.response as AuthenticatorAttestationResponse;
  const payload = {
    id: cred.id,
    type: cred.type,
    response: {
      clientDataJSON: b64uEnc(response.clientDataJSON),
      attestationObject: b64uEnc(response.attestationObject),
    }
  };

  return api.auth.registerVerify({ credential: payload, device_name: undefined, policy });
}

export async function loginPasskey() {
  const opts = await api.auth.loginOpts();
  const publicKey: PublicKeyCredentialRequestOptions = {
    challenge: b64uDec(opts.challenge),
    rpId: opts.rpId,
    userVerification: opts.userVerification as UserVerificationRequirement,
    timeout: opts.timeout,
  };

  const cred = await navigator.credentials.get({ publicKey }) as PublicKeyCredential;
  if (!cred) throw new Error("Passkey login cancelled or failed");

  const response = cred.response as AuthenticatorAssertionResponse;
  const payload = {
    id: cred.id,
    type: cred.type,
    response: {
      clientDataJSON: b64uEnc(response.clientDataJSON),
      authenticatorData: b64uEnc(response.authenticatorData),
      signature: b64uEnc(response.signature),
      userHandle: response.userHandle ? b64uEnc(response.userHandle) : null,
    }
  };

  return api.auth.loginVerify(payload);
}

export async function assertPasskey(opts: any) {
  const publicKey: PublicKeyCredentialRequestOptions = {
    challenge: b64uDec(opts.challenge),
    rpId: opts.rpId,
    userVerification: opts.userVerification as UserVerificationRequirement,
    timeout: opts.timeout,
  };

  if (opts.allowCredentials && opts.allowCredentials.length > 0) {
    publicKey.allowCredentials = opts.allowCredentials.map((c: any) => ({
      type: c.type,
      id: b64uDec(c.id),
    }));
  }

  const cred = await navigator.credentials.get({ publicKey }) as PublicKeyCredential;
  if (!cred) throw new Error("Passkey assertion cancelled or failed");

  const response = cred.response as AuthenticatorAssertionResponse;
  const payload = {
    id: cred.id,
    type: cred.type,
    response: {
      clientDataJSON: b64uEnc(response.clientDataJSON),
      authenticatorData: b64uEnc(response.authenticatorData),
      signature: b64uEnc(response.signature),
      userHandle: response.userHandle ? b64uEnc(response.userHandle) : null,
    }
  };

  return payload;
}

export async function registerPasskey(name = "Additional passkey") {
  const opts = await api.passkeys.registerOpts();
  const publicKey: PublicKeyCredentialCreationOptions = {
    challenge: b64uDec(opts.challenge),
    rp: { name: opts.rp.name, id: opts.rp.id },
    user: { id: b64uDec(opts.user.id), name: opts.user.name, displayName: opts.user.displayName },
    pubKeyCredParams: opts.pubKeyCredParams,
    authenticatorSelection: { ...opts.authenticatorSelection, residentKey: "required", userVerification: "required" },
    timeout: opts.timeout,
    attestation: "none",
  };
  const cred = await navigator.credentials.create({ publicKey }) as PublicKeyCredential;
  if (!cred) throw new Error("Passkey creation cancelled or failed");
  const response = cred.response as AuthenticatorAttestationResponse;
  return api.passkeys.registerVerify({
    credential: { id: cred.id, type: cred.type, response: { clientDataJSON: b64uEnc(response.clientDataJSON), attestationObject: b64uEnc(response.attestationObject) } },
    name,
  });
}
