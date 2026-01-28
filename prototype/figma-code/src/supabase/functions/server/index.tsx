import { Hono } from "npm:hono";
import { cors } from "npm:hono/cors";
import { logger } from "npm:hono/logger";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import * as kv from "./kv_store.tsx";

const app = new Hono();

// Enable logger
app.use('*', logger(console.log));

// Enable CORS for all routes and methods
app.use(
  "/*",
  cors({
    origin: "*",
    allowHeaders: ["Content-Type", "Authorization"],
    allowMethods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    exposeHeaders: ["Content-Length"],
    maxAge: 600,
  }),
);

// Health check endpoint
app.get("/make-server-a03ea467/health", (c) => {
  return c.json({ status: "ok" });
});

// Sign up endpoint
app.post("/make-server-a03ea467/signup", async (c) => {
  try {
    const { email, password, name } = await c.req.json();
    
    if (!email || !password || !name) {
      return c.json({ error: "Email, password, and name are required" }, 400);
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
    );

    const { data, error } = await supabase.auth.admin.createUser({
      email,
      password,
      user_metadata: { name },
      // Automatically confirm the user's email since an email server hasn't been configured.
      email_confirm: true
    });

    if (error) {
      console.log(`Error creating user during signup: ${error.message}`);
      return c.json({ error: error.message }, 400);
    }

    return c.json({ user: data.user });
  } catch (error) {
    console.log(`Error in signup endpoint: ${error}`);
    return c.json({ error: "Failed to create user" }, 500);
  }
});

// Save user preferences
app.post("/make-server-a03ea467/preferences", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    console.log('=== Preferences POST ===');
    
    if (!authHeader) {
      console.log('No Authorization header provided');
      return c.json({ error: "Unauthorized - No token" }, 401);
    }

    const body = await c.req.json();
    const { userId, ...preferences } = body;
    
    if (!userId) {
      console.log('No userId provided in request body');
      return c.json({ error: "userId is required" }, 400);
    }

    console.log(`Saving preferences for user ${userId}`);
    await kv.set(`user_preferences:${userId}`, preferences);

    console.log('Preferences saved successfully');
    return c.json({ success: true });
  } catch (error) {
    console.log(`Error saving preferences: ${error}`);
    return c.json({ error: "Failed to save preferences", details: error.message }, 500);
  }
});

// Get user preferences
app.get("/make-server-a03ea467/preferences", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    const userId = c.req.query('userId');
    
    if (!authHeader) {
      console.log('No Authorization header provided in preferences GET');
      return c.json({ error: "Unauthorized - No token" }, 401);
    }
    
    if (!userId) {
      console.log('No userId provided in query');
      return c.json({ error: "userId is required" }, 400);
    }

    const preferences = await kv.get(`user_preferences:${userId}`);
    console.log(`Retrieved preferences for user ${userId}:`, preferences);
    return c.json({ preferences });
  } catch (error) {
    console.log(`Error fetching preferences: ${error}`);
    return c.json({ error: "Failed to fetch preferences" }, 500);
  }
});

// Chat endpoint
app.post("/make-server-a03ea467/chat", async (c) => {
  try {
    const authHeader = c.req.header('Authorization');
    console.log('=== Chat POST ===');
    
    if (!authHeader) {
      console.log('No Authorization header provided');
      return c.json({ error: "Unauthorized - No token" }, 401);
    }

    const body = await c.req.json();
    const { userId, message } = body;
    
    if (!userId || !message) {
      console.log('userId or message missing in request body');
      return c.json({ error: "userId and message are required" }, 400);
    }

    console.log(`Chat message from user ${userId}: ${message}`);
    
    // TODO: 여기에 AI 모델 API 연동을 추가하세요
    // 현재는 임시 응답을 반환합니다
    const reply = `안녕하세요! "${message}"에 대한 답변을 준비 중입니다. AI 모델 연동 후 실제 답변이 제공됩니다.`;
    
    // 채팅 히스토리 저장 (선택사항)
    const chatKey = `chat_history:${userId}`;
    const existingHistory = await kv.get(chatKey) || [];
    const newHistory = [
      ...existingHistory,
      {
        userMessage: message,
        botReply: reply,
        timestamp: new Date().toISOString(),
      }
    ].slice(-50); // 최근 50개만 유지
    
    await kv.set(chatKey, newHistory);
    
    console.log('Chat reply sent successfully');
    return c.json({ reply });
  } catch (error) {
    console.log(`Error in chat endpoint: ${error}`);
    return c.json({ error: "Failed to process chat message", details: error.message }, 500);
  }
});

Deno.serve(app.fetch);