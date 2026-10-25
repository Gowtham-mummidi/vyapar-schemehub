import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.database import engine
from sqlalchemy import text

def setup_storage():
    print("Initializing Supabase Storage Buckets & Policies...")
    with engine.connect() as conn:
        # Create storage buckets
        conn.execute(text("""
            INSERT INTO storage.buckets (id, name, public, file_size_limit)
            VALUES 
                ('documents', 'documents', true, 52428800),
                ('schemes', 'schemes', true, 52428800)
            ON CONFLICT (id) DO UPDATE SET public = true;
        """))
        conn.commit()

        # Create policies if they do not exist
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE tablename = 'objects' AND schemaname = 'storage' AND policyname = 'Allow All documents'
                ) THEN
                    CREATE POLICY "Allow All documents" ON storage.objects 
                    FOR ALL USING (bucket_id = 'documents') WITH CHECK (bucket_id = 'documents');
                END IF;

                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies 
                    WHERE tablename = 'objects' AND schemaname = 'storage' AND policyname = 'Allow All schemes'
                ) THEN
                    CREATE POLICY "Allow All schemes" ON storage.objects 
                    FOR ALL USING (bucket_id = 'schemes') WITH CHECK (bucket_id = 'schemes');
                END IF;
            END $$;
        """))
        conn.commit()

        buckets = conn.execute(text("SELECT id, name, public FROM storage.buckets;")).fetchall()
        print("Storage buckets successfully configured:")
        for b in buckets:
            print(f" - Bucket '{b[0]}' (public: {b[2]})")

if __name__ == "__main__":
    setup_storage()
