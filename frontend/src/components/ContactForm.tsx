"use client";

import { useState } from "react";
import { site } from "@/config/site";

type Errors = Partial<Record<"name" | "email" | "message", string>>;

export function ContactForm() {
  const [f, setF] = useState({ name: "", email: "", message: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [sent, setSent] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const er: Errors = {};
    if (f.name.trim().length < 2) er.name = "Please tell us your name.";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) er.email = "Enter a valid email address.";
    if (f.message.trim().length < 10) er.message = "Please write at least 10 characters.";
    setErrors(er);
    if (Object.keys(er).length) return;
    // No backend yet: hand the message to the visitor's own mail app instead of pretending to send it.
    const body = encodeURIComponent(`${f.message}\n\n— ${f.name} (${f.email})`);
    window.location.href = `mailto:${site.contact.email}?subject=${encodeURIComponent("Message from the website")}&body=${body}`;
    setSent(true);
  };

  const field = (id: "name" | "email" | "message", label: string, el: React.ReactNode) => (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {el}
      {errors[id] && <span id={`${id}-err`} className="form-err" role="alert">{errors[id]}</span>}
    </div>
  );
  const common = (id: "name" | "email" | "message") => ({
    id, value: f[id], className: "input", "aria-invalid": !!errors[id], "aria-describedby": errors[id] ? `${id}-err` : undefined,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF({ ...f, [id]: e.target.value }),
  });

  if (sent) return (<div className="card" role="status"><h3>Your mail app should have opened</h3><p>This site has no mail server yet, so the message is handed to your email app. If nothing opened, write to <a href={`mailto:${site.contact.email}`}>{site.contact.email}</a>.</p></div>);
  return (
    <form className="card contact-form" onSubmit={submit} noValidate>
      {field("name", "Your name", <input {...common("name")} autoComplete="name" maxLength={80} />)}
      {field("email", "Email", <input {...common("email")} type="email" autoComplete="email" maxLength={120} />)}
      {field("message", "Message", <textarea {...common("message")} rows={6} maxLength={2000} />)}
      <button className="btn btn-primary" type="submit">Send message</button>
    </form>
  );
}
