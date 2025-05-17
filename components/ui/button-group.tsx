"use client"

import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

export interface ButtonGroupProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
}

export interface ButtonGroupItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string
  isSelected?: boolean
}

export function ButtonGroup({
  className,
  value,
  defaultValue,
  onValueChange,
  children,
  ...props
}: ButtonGroupProps) {
  const [selectedValue, setSelectedValue] = React.useState<string>(value || defaultValue || "")

  React.useEffect(() => {
    if (value !== undefined && value !== selectedValue) {
      setSelectedValue(value)
    }
  }, [value, selectedValue])

  const handleValueChange = (newValue: string) => {
    setSelectedValue(newValue)
    onValueChange?.(newValue)
  }

  return (
    <div className={cn("flex w-full", className)} {...props}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement<ButtonGroupItemProps>(child)) {
          return React.cloneElement(child, {
            isSelected: child.props.value === selectedValue,
            onClick: () => handleValueChange(child.props.value)
          })
        }
        return child
      })}
    </div>
  )
}

export function ButtonGroupItem({
  className,
  value,
  isSelected,
  children,
  ...props
}: ButtonGroupItemProps) {
  return (
    <Button
      variant={isSelected ? "default" : "outline"}
      className={cn(
        "flex-1 rounded-none first:rounded-l-md last:rounded-r-md border-r-0 last:border-r",
        isSelected ? "bg-primary text-primary-foreground hover:bg-primary/90" : "bg-transparent",
        className
      )}
      {...props}
    >
      {children}
    </Button>
  )
} 