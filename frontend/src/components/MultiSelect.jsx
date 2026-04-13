import React, { useState } from 'react';
import { Check, ChevronsUpDown, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { Badge } from '@/components/ui/badge';

export function MultiSelect({ 
  selected, 
  onSelectionChange, 
  options, 
  placeholder = "Select options...", 
  searchPlaceholder = "Search...",
  emptyMessage = "No results found."
}) {
  const [open, setOpen] = useState(false);

  const handleSelect = (value) => {
    const newSelection = selected.includes(value)
      ? selected.filter((item) => item !== value)
      : [...selected, value];
    onSelectionChange(newSelection);
  };

  const handleRemove = (e, value) => {
    e.stopPropagation();
    onSelectionChange(selected.filter((item) => item !== value));
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onSelectionChange([]);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between h-auto min-h-[40px] px-3 py-2"
        >
          <div className="flex flex-wrap gap-1 items-center">
            {selected.length > 0 ? (
              <>
                {selected.slice(0, 2).map((val) => (
                  <Badge 
                    key={val} 
                    variant="secondary" 
                    className="mr-1 bg-blue-50 text-blue-700 hover:bg-blue-100 border-blue-200"
                  >
                    {val}
                    <X 
                      className="ml-1 h-3 w-3 cursor-pointer" 
                      onClick={(e) => handleRemove(e, val)}
                    />
                  </Badge>
                ))}
                {selected.length > 2 && (
                  <span className="text-xs text-muted-foreground">+{selected.length - 2} more</span>
                )}
              </>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
          </div>
          <div className="flex items-center">
            {selected.length > 0 && (
              <X 
                className="h-4 w-4 mr-2 opacity-50 hover:opacity-100" 
                onClick={handleClear}
              />
            )}
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0" style={{ width: 'var(--radix-popover-trigger-width)' }}>
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyMessage}</CommandEmpty>
            <CommandGroup className="max-h-64 overflow-auto">
              {options.map((option) => (
                <CommandItem
                  key={option.value}
                  onSelect={() => handleSelect(option.value)}
                  className="flex items-center gap-2"
                >
                  <div className={cn(
                    "flex h-4 w-4 items-center justify-center rounded border border-primary transition-colors",
                    selected.includes(option.value) ? "bg-primary text-primary-foreground" : "opacity-50"
                  )}>
                    {selected.includes(option.value) && <Check className="h-3 w-3" />}
                  </div>
                  {option.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
