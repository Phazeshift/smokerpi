import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { FormInput } from './forminput';

test('renders a labelled input with the given value', () => {
  render(
    <FormInput
      label="Target temperature"
      name="set_temperature"
      value="105"
      placeholder="Enter value..."
      onChange={() => {}}
    />
  );

  expect(screen.getByLabelText('Target temperature')).toHaveValue('105');
});

test('calls onChange when the user types', () => {
  const handleChange = vi.fn();
  render(
    <FormInput
      label="Target temperature"
      name="set_temperature"
      value=""
      placeholder="Enter value..."
      onChange={handleChange}
    />
  );

  fireEvent.change(screen.getByLabelText('Target temperature'), { target: { value: '130' } });

  expect(handleChange).toHaveBeenCalled();
});

test('shows the error message when an error is passed', () => {
  render(
    <FormInput
      label="Target temperature"
      name="set_temperature"
      value=""
      placeholder="Enter value..."
      onChange={() => {}}
      error="Enter value"
    />
  );

  expect(screen.getByText('Enter value')).toBeInTheDocument();
});

test('defaults to a text input and only adds the className it is given', () => {
  render(
    <FormInput
      label="Target temperature"
      name="set_temperature"
      value=""
      placeholder="Enter value..."
      onChange={() => {}}
    />
  );

  const input = screen.getByLabelText('Target temperature');
  expect(input).toHaveAttribute('type', 'text');
  expect(input).toHaveClass('form-control');
});

test('can be disabled', () => {
  render(
    <FormInput
      label="Max CS Pin"
      name="cs_pin"
      value="20"
      placeholder="Enter value..."
      onChange={() => {}}
      disabled
    />
  );

  expect(screen.getByLabelText('Max CS Pin')).toBeDisabled();
});
