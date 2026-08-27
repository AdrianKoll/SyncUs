BEGIN;

-- O par passa a ter uma representação canônica, independentemente de quem
-- enviou ou aceitou o convite.
UPDATE couple_connections
SET user1_id = LEAST(user1_id, user2_id),
    user2_id = GREATEST(user1_id, user2_id)
WHERE user1_id > user2_id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_couple_connections_ordered_users'
    ) THEN
        ALTER TABLE couple_connections
            ADD CONSTRAINT ck_couple_connections_ordered_users
            CHECK (user1_id < user2_id);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_couple_user1
    ON couple_connections (user1_id)
    WHERE is_active = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_couple_user2
    ON couple_connections (user2_id)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS couple_connection_members (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER NOT NULL
        REFERENCES couple_connections(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_couple_connection_member_pair
        UNIQUE (connection_id, user_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_couple_member_user
    ON couple_connection_members (user_id)
    WHERE is_active = TRUE;

-- O INSERT falha propositalmente se os dados existentes já tiverem o mesmo
-- usuário em mais de uma conexão ativa. Nesse caso, resolva o conflito antes
-- de disponibilizar a nova versão da aplicação.
INSERT INTO couple_connection_members (connection_id, user_id, is_active)
SELECT connection_id, user_id, TRUE
FROM (
    SELECT id AS connection_id, user1_id AS user_id
    FROM couple_connections
    WHERE is_active = TRUE
    UNION ALL
    SELECT id AS connection_id, user2_id AS user_id
    FROM couple_connections
    WHERE is_active = TRUE
) AS active_members
ON CONFLICT (connection_id, user_id)
DO UPDATE SET is_active = EXCLUDED.is_active;

COMMIT;
