import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { api } from "@/lib/api";
import { UploadCloud } from "lucide-react";

interface Props {
  onSuccess: (data: any) => void;
}

export default function DropZone({ onSuccess }: Props) {
  const [isUploading, setUploading] = useState(false);
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles.length) return;
    const file = acceptedFiles[0];
    const form = new FormData();
    form.append("file", file);
    setUploading(true);
    try {
      const { data } = await api.post("/extract/", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onSuccess(data);
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    } finally {
      setUploading(false);
    }
  }, [onSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { "application/pdf": [] } });

  return (
    <div
      {...getRootProps()}
      className="border-2 border-dashed border-gray-600 rounded-xl p-10 text-center cursor-pointer hover:bg-background-light transition-colors"
    >
      <input {...getInputProps()} />
      {isUploading ? (
        <p className="animate-pulse text-primary">Uploading…</p>
      ) : (
        <>
          <UploadCloud size={48} className="mx-auto text-primary" />
          <p className="mt-4 text-lg">
            {isDragActive ? "Drop the PDF here…" : "Drag and drop a scanned PDF here or click to upload"}
          </p>
          <p className="text-sm text-accent">Saving you time so you can make more money</p>
        </>
      )}
    </div>
  );
} 