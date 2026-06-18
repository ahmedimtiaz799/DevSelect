-- STAGING INIT DRAFT
-- REVIEW BEFORE APPLYING
-- APPLY TO STAGING ONLY
-- DO NOT APPLY TO PRODUCTION WITHOUT SEPARATE REVIEW
--
-- Purpose:
--   Initialize the minimal DevSelect application schema in a new/empty
--   Supabase staging project before applying later hardening/index drafts.
--
-- Do not apply this blindly. Confirm the target project is staging first.
--
-- Not included here:
--   - LangGraph checkpoint tables. Those should be created/checked by the
--     LangGraph Postgres checkpointer during normal backend startup.
--   - Grant hardening. Apply 001_harden_table_grants.sql after schema exists.
--   - Extra performance indexes. Apply 002_add_core_indexes.sql after schema exists.

create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists public.chats (
  id uuid not null default gen_random_uuid(),
  user_id uuid not null,
  title text default 'New Chat',
  thread_id text,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now(),
  candidate_embedding vector(1024),
  is_pinned boolean default false,
  pinned_at timestamp with time zone,
  constraint chats_pkey primary key (id),
  constraint chats_user_id_fkey foreign key (user_id) references auth.users(id)
);

create table if not exists public.messages (
  id uuid not null default gen_random_uuid(),
  chat_id uuid not null,
  role text,
  content text,
  created_at timestamp with time zone default now(),
  message_type text,
  constraint messages_pkey primary key (id),
  constraint messages_chat_id_fkey foreign key (chat_id)
    references public.chats(id) on delete cascade,
  constraint messages_role_check check (role in ('user', 'assistant', 'status'))
);

alter table public.chats enable row level security;
alter table public.messages enable row level security;

drop policy if exists "users own chats" on public.chats;
create policy "users own chats"
on public.chats
for all
to authenticated
using (user_id = auth.uid())
with check (user_id = auth.uid());

drop policy if exists "user's own messages" on public.messages;
create policy "user's own messages"
on public.messages
for all
to authenticated
using (
  exists (
    select 1
    from public.chats c
    where c.id = messages.chat_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.chats c
    where c.id = messages.chat_id
      and c.user_id = auth.uid()
  )
);
