import { z } from 'zod'

export const workspaceSchema = z.object({ id: z.string(), directory: z.string() })
export const saveRequest = z
  .object({
    content: z.string(),
    original: z.string(),
  })
  .strict()
export const fileEventSchema = z.object({ file: z.string() })
export const openedFileSchema = z.object({
  workspace: workspaceSchema,
  file: z.string(),
  hash: z.string(),
})
export type Workspace = z.infer<typeof workspaceSchema>

export interface FileNode {
  id: string
  name: string
  children?: FileNode[]
}

export const fileNodeSchema: z.ZodType<FileNode> = z.object({
  id: z.string(),
  name: z.string(),
  children: z.lazy(() => z.array(fileNodeSchema)).optional(),
})
export const treeSchema = z.array(fileNodeSchema)
