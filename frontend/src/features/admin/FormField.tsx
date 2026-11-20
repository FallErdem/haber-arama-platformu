import { Label, Text, TextField } from 'react-aria-components'
import { Input } from '../../components/ui/input'

interface FormFieldProps {
  label: string
  value: string
  onChange: (value: string) => void
  /** API bu alanı geçersiz bulduysa; alan kırmızı çerçeveyle işaretlenir ve ekran okuyucu bildirir. */
  isInvalid?: boolean
  isRequired?: boolean
  description?: string
  type?: 'text' | 'url' | 'number'
}

/**
 * Yönetim formlarının metin alanı. React Aria'nın `TextField` bileşeni etiketi, açıklamayı ve geçersizlik
 * durumunu alana kendiliğinden bağlar (`aria-labelledby`, `aria-describedby`, `aria-invalid`).
 */
export function FormField({
  label,
  value,
  onChange,
  isInvalid,
  isRequired,
  description,
  type = 'text',
}: FormFieldProps) {
  return (
    <TextField
      value={value}
      onChange={onChange}
      isInvalid={isInvalid}
      isRequired={isRequired}
      type={type}
      className="flex flex-col gap-1"
    >
      <Label className="text-sm font-medium">{label}</Label>
      <Input className="data-invalid:border-destructive" />
      {description && (
        <Text slot="description" className="text-xs text-muted-foreground">
          {description}
        </Text>
      )}
    </TextField>
  )
}
