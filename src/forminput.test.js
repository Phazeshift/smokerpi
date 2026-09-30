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
  const handleChange = jest.fn();
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
