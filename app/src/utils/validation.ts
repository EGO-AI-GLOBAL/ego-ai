export function validateEmail(email: string): string | null {
  const v = email.trim();
  if (!v) return "Informe o e-mail.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return "E-mail inválido.";
  if (v.length > 254) return "E-mail demasiado longo.";
  return null;
}

export function validatePassword(password: string): string | null {
  if (!password) return "Informe a senha.";
  if (password.length < 6) return "A senha deve ter pelo menos 6 caracteres.";
  return null;
}

/** Telefone BR opcional; se preenchido, valida DDD+número. */
export function validatePhone(phone: string, required = false): string | null {
  const v = phone.trim();
  if (!v) return required ? "Informe o telefone com DDD." : null;
  const digits = v.replace(/\D/g, "");
  if (digits.length < 10 || digits.length > 13) {
    return "Telefone inválido. Ex.: 11 99999-9999";
  }
  return null;
}

export function validatePasswordConfirm(
  password: string,
  confirm: string
): string | null {
  const passErr = validatePassword(password);
  if (passErr) return passErr;
  if (!confirm) return "Confirme a senha.";
  if (password !== confirm) return "As senhas não coincidem.";
  return null;
}
