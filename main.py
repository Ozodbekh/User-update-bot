import asyncio
import logging
import sys
from os import getenv

import psycopg2
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, KeyboardButton, BotCommand
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
load_dotenv()

TOKEN = getenv("BOT_TOKEN")

dp = Dispatcher()

connect = psycopg2.connect(
    dbname = getenv("DB_NAME"),
    user = getenv("USERNAME"),
    password = getenv("PASSWORD"),
    host = getenv("HOST")
)

cursor = connect.cursor()

cursor.execute(
    """
        create table if not exists users(
            id serial,
            user_id bigint primary key,
            username varchar,
            firstname varchar,
            lastname varchar,
            phone_number varchar,
            started_at timestamp default current_timestamp
        );
    """
               )

cursor.execute(
    """
        create table if not exists medias(
            id serial,
            user_id bigint references users(user_id),
            file_id varchar,
            file_type varchar,
            created_at timestamp default current_timestamp
        );
    """
            )

connect.commit()

def phone_number_button():
    rkb = ReplyKeyboardBuilder()
    rkb.add(KeyboardButton(text="Share contact", request_contact=True))
    rkb.adjust(1)
    return rkb.as_markup(resize_keyboard=True)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/media", description="Displays the information about the media you have sent.")
    ]
    await bot.set_my_commands(commands)
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    cursor.execute("select user_id from users where user_id=%s", (user_id, ))
    if cursor.fetchone() is None:
        await message.answer(f"Assalomu alaykum, {html.bold(message.from_user.full_name)}!")
        await message.answer(text="You should share your contact", reply_markup=phone_number_button())
    else:
        await message.answer_photo(photo="https://telegra.ph/file/0c49ea8828ec8036fea54.png")
        await message.answer(f"Welcome back, {html.bold(message.from_user.full_name)}")

@dp.message(F.contact)
async def contact_handler(message: Message) -> None:
    user_id = message.from_user.id
    cursor.execute("select user_id from users where user_id=%s", (user_id,))
    if cursor.fetchone() is None:
        phone_number = message.contact.phone_number
        cursor.execute("""
                        insert into users(user_id, username, firstname, lastname, phone_number, started_at) values (%s, %s, %s, %s, %s, now())""",
                       (user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name, phone_number)
                       )
        connect.commit()
        await message.answer("Welcome, Your information has been saved.")

@dp.message(F.photo | F.video | F.document)
async def media_handler(message: Message) -> None:
    file_id = None
    file_type = None

    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'

    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'

    elif message.document:
        file_id = message.document.file_id
        file_type = 'document'

    cursor.execute("insert into medias(user_id, file_id, file_type, created_at) values (%s, %s, %s, now())",
                   (message.from_user.id, file_id, file_type)
                    )
    connect.commit()
    await message.reply("Information of media has been saved successfully!")


@dp.message(Command('media'))
async def show_information_of_medias(message: Message):
    user_id = message.from_user.id
    cursor.execute("select user_id from medias where user_id=%s", (user_id,))
    if cursor.fetchone():
        cursor.execute("select file_id, file_type, created_at from medias where user_id = %s", (user_id,))
        media_data = cursor.fetchall()
        response = "Here are the media files you have sent:\n"
        for file_id, file_type, created_at in media_data:
            response += f" File id: {file_id}\n File type: {file_type}\n Sent at: {created_at}\n\n"
        await message.answer(response)
    else:
        await message.answer("You haven't sent any media to the bot.")


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await set_bot_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())




