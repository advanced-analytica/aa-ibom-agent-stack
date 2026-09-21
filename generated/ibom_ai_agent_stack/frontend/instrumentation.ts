import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "ibom_ai_agent_stack-frontend",
  });
}
