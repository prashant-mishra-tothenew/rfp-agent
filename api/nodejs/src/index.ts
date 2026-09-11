import cors from "@fastify/cors";
import multipart from "@fastify/multipart";
import Fastify from "fastify";
import { rfpRoutes } from "./routes/rfp.js";

const UPLOAD_MAX_FILE_BYTES = parseInt(
  process.env.UPLOAD_MAX_FILE_BYTES || String(50 * 1024 * 1024),
  10
);

const app = Fastify({
  logger: true,
  bodyLimit: UPLOAD_MAX_FILE_BYTES,
});

await app.register(cors, { origin: true });
await app.register(multipart, {
  limits: {
    fileSize: UPLOAD_MAX_FILE_BYTES,
    files: 20,
  },
});
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
