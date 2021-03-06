import sys
import actions as ac


def main():
    print('\n')
    print('Postman Courier App')
    print('')
    print('Press:')
    print('1 - for login')
    print('2 - for register')
    print('3 - for exit')
    option = read_options(input("Option: "), 1, 3)

    if option == 1:
        username = ac.start_login()
        ac.start_getting_labels(username)

        while option != 4:
            print('')
            print('Press:')
            print('1 - to show labels')
            print('2 - to add package')
            print('3 - to change package status')
            print('4 - for exit')
            option = read_options(input("Option: "), 1, 4)
            if option == 1:
                ac.start_getting_labels(username)
            if option == 2:
                ac.start_adding_package(username)
            if option == 3:
                ac.start_changing_package_status(username)
    if option == 2:
        ac.start_register()
        print('Press:')
        print('1 - for login')
        print('2 - for exit')
        option = read_options(input("Option: "), 1, 2)
        if option == 1:
            username = ac.start_login()
            ac.start_getting_labels(username)

            while option != 4:
                print('')
                print('Press:')
                print('1 - to show labels')
                print('2 - to add package')
                print('3 - to change package status')
                print('4 - for exit')
                option = read_options(input("Option: "), 1, 4)
                if option == 1:
                    ac.start_getting_labels(username)
                if option == 2:
                    ac.start_adding_package(username)
                if option == 3:
                    ac.start_changing_package_status(username)
        if option == 2:
            print('\nSee you next time')
            sys.exit(0)
    else:
        print('\nSee you next time')
        sys.exit(0)

    print('\nSee you next time')


def read_options(inp, input_limit, input_limit1):
    try:
        inp = int(inp)
    except ValueError:
        print(
            f'Option must be a number between {input_limit} and {input_limit1}\n')
        sys.exit(0)
    if inp < input_limit or inp > input_limit1:
        print(
            f'Option must be a number between {input_limit} and {input_limit1}\n')
        sys.exit(0)
    return inp


if __name__ == "__main__":
    main()
