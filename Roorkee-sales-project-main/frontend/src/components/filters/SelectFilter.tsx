import { FormControl, InputLabel, MenuItem, Select } from '@mui/material'

export interface SelectFilterOption {
  value: string
  label: string
}

interface SelectFilterProps {
  label: string
  value: string
  onChange: (value: string) => void
  options: SelectFilterOption[]
  minWidth?: number
}

const ALL_VALUE = '__all__'

export function SelectFilter({ label, value, onChange, options, minWidth = 160 }: SelectFilterProps) {
  return (
    <FormControl size="small" sx={{ minWidth }}>
      <InputLabel id={`${label}-filter-label`}>{label}</InputLabel>
      <Select
        labelId={`${label}-filter-label`}
        label={label}
        value={value || ALL_VALUE}
        onChange={(e) => onChange(e.target.value === ALL_VALUE ? '' : e.target.value)}
      >
        <MenuItem value={ALL_VALUE}>All</MenuItem>
        {options.map((opt) => (
          <MenuItem key={opt.value} value={opt.value}>
            {opt.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}
