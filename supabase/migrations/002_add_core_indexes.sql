-- DevSelect D1 hardening: core indexes.
--
-- These use normal CREATE INDEX IF NOT EXISTS because migration runners often
-- execute files inside a transaction. Do not use CONCURRENTLY here unless the
-- migration runner is confirmed to allow non-transactional statements.
--
-- Verify column names before applying to a real Supabase project.

create index if not exists idx_chats_user_id
on public.chats (user_id);

create index if not exists idx_chats_user_id_updated_at_desc
on public.chats (user_id, updated_at desc);

create index if not exists idx_messages_chat_id_created_at
on public.messages (chat_id, created_at);
