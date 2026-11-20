import MDEditor from '@uiw/react-md-editor'

interface Props {
  value: string
  onChange: (value: string) => void
}

function handleChange(onChange: Props['onChange'], val: string | undefined) {
  onChange(val ?? '')
}

function EditorPane({ value, onChange }: Props) {
  return (
    <div className="editor-pane" data-testid="editor-pane">
      <MDEditor
        value={value}
        onChange={(val) => handleChange(onChange, val)}
        preview="edit"
        height="100%"
      />
    </div>
  )
}

export default EditorPane
