import cors from "@fastify/cors";
import multipart from "@fastify/multipart";
import Fastify from "fastify";
import { rfpRoutes } from "./routes/rfp.js";

const app = Fastify({ logger: true });

await app.register(cors, { origin: true });
await app.register(multipart);
await app.register(rfpRoutes);

app.get("/health", async () => ({ status: "ok", service: "rfp-agent-api" }));

const port = parseInt(process.env.PORT || "3001", 10);
const host = process.env.HOST || "0.0.0.0";

app.listen({ port, host }, (err) => {
  if (err) {
    app.log.error(err);
    process.exit(1);
  }
});
